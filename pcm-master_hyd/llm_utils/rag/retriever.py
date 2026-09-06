import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from .index import SCHEMA_VERSION
from .text import normalize_text, phrase_similarity, search_tokens, unique_phrases


MAX_ITEMS_PER_FIELD = 20
MAX_ITEM_LENGTH = 240
MAX_QUERY_TOKENS = 96
MAX_CANDIDATES = 1200


@dataclass(frozen=True)
class RetrievalQuery:
    free_text: str = ""
    symptoms: tuple[str, ...] = ()
    tongue: tuple[str, ...] = ()
    pulse: tuple[str, ...] = ()
    complexion: tuple[str, ...] = ()
    voice: tuple[str, ...] = ()
    mechanisms: tuple[str, ...] = ()
    syndromes: tuple[str, ...] = ()
    treatments: tuple[str, ...] = ()
    formula_names: tuple[str, ...] = ()
    doctor_notes: tuple[str, ...] = ()
    top_k: int = 5

    @classmethod
    def from_mapping(cls, data: dict) -> "RetrievalQuery":
        if not isinstance(data, dict):
            raise ValueError("检索请求必须是对象")

        def items(key: str) -> tuple[str, ...]:
            value = data.get(key)
            if value in (None, ""):
                return ()
            if isinstance(value, str):
                raw_values = [value]
            elif isinstance(value, (list, tuple)):
                raw_values = list(value)
            else:
                raise ValueError(f"{key} 必须是字符串或字符串数组")
            if len(raw_values) > MAX_ITEMS_PER_FIELD:
                raise ValueError(f"{key} 最多允许 {MAX_ITEMS_PER_FIELD} 项")
            phrases = unique_phrases(raw_values)
            if any(len(phrase) > MAX_ITEM_LENGTH for phrase in phrases):
                raise ValueError(f"{key} 单项不能超过 {MAX_ITEM_LENGTH} 个字符")
            return tuple(phrases)

        try:
            top_k = int(data.get("top_k", 5))
        except (TypeError, ValueError) as exc:
            raise ValueError("top_k 必须是整数") from exc
        if not 1 <= top_k <= 20:
            raise ValueError("top_k 必须在 1—20 之间")

        free_text = normalize_text(data.get("free_text", ""))
        if len(free_text) > 1000:
            raise ValueError("free_text 不能超过 1000 个字符")
        query = cls(
            free_text=free_text,
            symptoms=items("symptoms"),
            tongue=items("tongue"),
            pulse=items("pulse"),
            complexion=items("complexion"),
            voice=items("voice"),
            mechanisms=items("mechanisms"),
            syndromes=items("syndromes"),
            treatments=items("treatments"),
            formula_names=items("formula_names"),
            doctor_notes=items("doctor_notes"),
            top_k=top_k,
        )
        if not query.all_phrases:
            raise ValueError("至少提供一项症状、四诊、病机、治法、方名或自由检索文本")
        return query

    @property
    def all_phrases(self) -> tuple[str, ...]:
        return tuple(
            unique_phrases(
                [
                    self.free_text,
                    *self.symptoms,
                    *self.tongue,
                    *self.pulse,
                    *self.complexion,
                    *self.voice,
                    *self.mechanisms,
                    *self.syndromes,
                    *self.treatments,
                    *self.formula_names,
                    *self.doctor_notes,
                ]
            )
        )

    def as_dict(self) -> dict:
        return {
            "free_text": self.free_text,
            "symptoms": list(self.symptoms),
            "tongue": list(self.tongue),
            "pulse": list(self.pulse),
            "complexion": list(self.complexion),
            "voice": list(self.voice),
            "mechanisms": list(self.mechanisms),
            "syndromes": list(self.syndromes),
            "treatments": list(self.treatments),
            "formula_names": list(self.formula_names),
            "doctor_notes": list(self.doctor_notes),
            "top_k": self.top_k,
        }


@dataclass
class _CandidateState:
    retrieval_score: float = 0.0
    routes: set[str] = field(default_factory=set)
    syndrome_hits: list[dict] = field(default_factory=list)


class FormulaRetriever:
    """方名、字段全文及附编病证索引的混合召回与可解释重排。"""

    _COLUMN_WEIGHTS = "12.0, 7.0, 9.0, 1.5, 3.0, 1.0"
    _FTS_ROUTES = (
        ("方名", "formula_names", "name_terms", 36.0),
        ("治法", "treatments", "action_terms", 18.0),
        ("证型", "syndromes", "indication_terms", 17.0),
        ("病机", "mechanisms", "indication_terms", 14.0),
        ("症状", "symptoms", "indication_terms", 13.0),
        ("舌象", "tongue", "indication_terms", 10.0),
        ("脉象", "pulse", "indication_terms", 10.0),
        ("全字段", "all_phrases", "all_terms", 5.0),
    )
    _SCORING_FIELDS = {
        "formula_names": (("name", 90.0, "方名"),),
        "treatments": (
            ("actions", 18.0, "功用"),
            ("indications", 7.0, "主治"),
            ("other_text", 3.0, "正文"),
        ),
        "syndromes": (
            ("indications", 17.0, "主治"),
            ("actions", 7.0, "功用"),
            ("other_text", 4.0, "正文"),
        ),
        "mechanisms": (
            ("indications", 14.0, "主治"),
            ("actions", 7.0, "功用"),
            ("other_text", 4.0, "正文"),
        ),
        "symptoms": (
            ("indications", 12.0, "主治"),
            ("modifications", 4.0, "加减"),
            ("other_text", 2.0, "正文"),
        ),
        "tongue": (("indications", 10.0, "主治"), ("other_text", 3.0, "正文")),
        "pulse": (("indications", 10.0, "主治"), ("other_text", 3.0, "正文")),
        "complexion": (("indications", 8.0, "主治"), ("other_text", 2.0, "正文")),
        "voice": (("indications", 7.0, "主治"), ("other_text", 2.0, "正文")),
        "doctor_notes": (
            ("indications", 7.0, "主治"),
            ("actions", 5.0, "功用"),
            ("other_text", 2.0, "正文"),
        ),
        "free_text": (
            ("name", 12.0, "方名"),
            ("indications", 8.0, "主治"),
            ("actions", 6.0, "功用"),
            ("other_text", 2.0, "正文"),
        ),
    }

    def __init__(self, index_path: Path):
        self.index_path = Path(index_path)

    def _connect(self) -> sqlite3.Connection:
        if not self.index_path.is_file():
            raise FileNotFoundError(
                f"RAG 索引尚未构建：{self.index_path}。请先执行 build_fangji_index。"
            )
        uri = f"file:{quote(str(self.index_path.resolve()))}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def metadata(self) -> dict:
        with self._connect() as connection:
            metadata = {
                row["key"]: json.loads(row["value"])
                for row in connection.execute("SELECT key, value FROM metadata")
            }
        if metadata.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError("RAG 索引版本与当前程序不一致，请重新构建")
        return metadata

    def search(self, query: RetrievalQuery | dict, full_fields: bool = False) -> dict:
        if isinstance(query, dict):
            query = RetrievalQuery.from_mapping(query)

        states: defaultdict[str, _CandidateState] = defaultdict(_CandidateState)
        with self._connect() as connection:
            self._verify_schema(connection)
            self._recall_exact_names(connection, query, states)
            self._recall_fts(connection, query, states)
            self._recall_syndromes(connection, query, states)
            if not states:
                self._recall_like_fallback(connection, query, states)

            if not states:
                candidates = []
            else:
                candidate_ids = sorted(
                    states,
                    key=lambda formula_id: states[formula_id].retrieval_score,
                    reverse=True,
                )[:MAX_CANDIDATES]
                ranked = [
                    self._rank_record(row, states[row["id"]], query, full_fields=full_fields)
                    for row in self._fetch_records(connection, candidate_ids)
                ]
                ranked.sort(key=lambda item: (-item["_score"], -item["evidence_coverage"], item["id"]))
                candidates = self._diversify(ranked, query.top_k)
                for candidate in candidates:
                    candidate.pop("_score", None)

            metadata = {
                row["key"]: json.loads(row["value"])
                for row in connection.execute(
                    "SELECT key, value FROM metadata WHERE key IN "
                    "('schema_version', 'built_at', 'indexed_records', 'excluded_records')"
                )
            }

        return {
            "query": query.as_dict(),
            "candidates": candidates,
            "retrieval": {
                "candidate_pool": len(states),
                "returned": len(candidates),
                "index": metadata,
                "score_note": "证据覆盖率和检索分值只用于候选排序，不代表临床有效率。",
            },
        }

    @staticmethod
    def _verify_schema(connection: sqlite3.Connection) -> None:
        row = connection.execute(
            "SELECT value FROM metadata WHERE key='schema_version'"
        ).fetchone()
        if row is None or json.loads(row["value"]) != SCHEMA_VERSION:
            raise RuntimeError("RAG 索引版本与当前程序不一致，请重新构建")

    @staticmethod
    def _add_candidate(
        states: defaultdict[str, _CandidateState],
        formula_id: str,
        score: float,
        route: str,
    ) -> _CandidateState:
        state = states[formula_id]
        state.retrieval_score += score
        state.routes.add(route)
        return state

    def _recall_exact_names(
        self,
        connection: sqlite3.Connection,
        query: RetrievalQuery,
        states: defaultdict[str, _CandidateState],
    ) -> None:
        for name in query.formula_names:
            escaped = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = connection.execute(
                """
                SELECT id, name FROM formulas
                WHERE name = ? OR name LIKE ? ESCAPE '\\'
                LIMIT 100
                """,
                (name, f"%{escaped}%"),
            )
            for row in rows:
                exact = normalize_text(row["name"]) == normalize_text(name)
                self._add_candidate(
                    states, row["id"], 100.0 if exact else 55.0, "方名精确匹配" if exact else "方名包含匹配"
                )

    def _recall_fts(
        self,
        connection: sqlite3.Connection,
        query: RetrievalQuery,
        states: defaultdict[str, _CandidateState],
    ) -> None:
        for label, attribute, column, boost in self._FTS_ROUTES:
            values = query.all_phrases if attribute == "all_phrases" else getattr(query, attribute)
            tokens = list(dict.fromkeys(search_tokens(values)))[:MAX_QUERY_TOKENS]
            if not tokens:
                continue
            expression = self._match_expression(column, tokens)
            rows = connection.execute(
                f"""
                SELECT f.id, -bm25(formula_fts, {self._COLUMN_WEIGHTS}) AS relevance
                FROM formula_fts
                JOIN formulas AS f ON f.rowid = formula_fts.rowid
                WHERE formula_fts MATCH ?
                ORDER BY bm25(formula_fts, {self._COLUMN_WEIGHTS})
                LIMIT 360
                """,
                (expression,),
            )
            for row in rows:
                relevance = max(0.0, float(row["relevance"] or 0.0))
                self._add_candidate(
                    states,
                    row["id"],
                    boost + min(14.0, relevance * 2.5),
                    f"{label}字段召回",
                )

    @staticmethod
    def _match_expression(column: str, tokens: list[str]) -> str:
        safe = [token.replace('"', '""') for token in tokens if token]
        return f"{column}: (" + " OR ".join(f'"{token}"' for token in safe) + ")"

    def _recall_syndromes(
        self,
        connection: sqlite3.Connection,
        query: RetrievalQuery,
        states: defaultdict[str, _CandidateState],
    ) -> None:
        terms = unique_phrases([*query.symptoms, *query.syndromes, query.free_text])
        for term in terms[:30]:
            if len(term) < 2:
                continue
            rows = connection.execute(
                """
                SELECT st.term, st.major_category, st.minor_category,
                       st.pdf_pages, st.book_pages, sl.formula_id,
                       CASE WHEN st.term = ? THEN 1 ELSE 0 END AS exact_match
                FROM syndrome_terms AS st
                JOIN syndrome_links AS sl ON sl.syndrome_id = st.id
                WHERE st.term = ? OR instr(st.term, ?) > 0 OR instr(?, st.term) > 0
                ORDER BY exact_match DESC
                LIMIT 500
                """,
                (term, term, term, term),
            )
            for row in rows:
                exact = bool(row["exact_match"])
                state = self._add_candidate(
                    states,
                    row["formula_id"],
                    22.0 if exact else 9.0,
                    "附编病证索引",
                )
                hit = {
                    "query_term": term,
                    "index_term": row["term"],
                    "category": {
                        "major": row["major_category"],
                        "minor": row["minor_category"],
                    },
                    "source": {
                        "volume": 11,
                        "pdf_pages": json.loads(row["pdf_pages"]),
                        "book_pages": json.loads(row["book_pages"]),
                    },
                }
                if hit not in state.syndrome_hits:
                    state.syndrome_hits.append(hit)

    def _recall_like_fallback(
        self,
        connection: sqlite3.Connection,
        query: RetrievalQuery,
        states: defaultdict[str, _CandidateState],
    ) -> None:
        for phrase in query.all_phrases[:10]:
            escaped = phrase.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            rows = connection.execute(
                """
                SELECT id FROM formulas
                WHERE name LIKE ? ESCAPE '\\'
                   OR indications LIKE ? ESCAPE '\\'
                   OR actions LIKE ? ESCAPE '\\'
                LIMIT 300
                """,
                (f"%{escaped}%", f"%{escaped}%", f"%{escaped}%"),
            )
            for row in rows:
                self._add_candidate(states, row["id"], 4.0, "短词兜底召回")

    @staticmethod
    def _fetch_records(connection: sqlite3.Connection, formula_ids: list[str]) -> list[sqlite3.Row]:
        records: list[sqlite3.Row] = []
        for offset in range(0, len(formula_ids), 500):
            batch = formula_ids[offset : offset + 500]
            placeholders = ",".join("?" for _ in batch)
            records.extend(
                connection.execute(
                    f"SELECT * FROM formulas WHERE id IN ({placeholders})", batch
                ).fetchall()
            )
        return records

    def _rank_record(
        self,
        row: sqlite3.Row,
        state: _CandidateState,
        query: RetrievalQuery,
        full_fields: bool = False,
    ) -> dict:
        score = state.retrieval_score
        matched_weight = 0.0
        possible_weight = 0.0
        matched_terms: defaultdict[str, list[str]] = defaultdict(list)
        reasons = list(sorted(state.routes))
        richness = sum(
            bool(row[field])
            for field in (
                "source_text",
                "composition",
                "usage_text",
                "actions",
                "indications",
                "modifications",
                "cautions",
                "other_text",
            )
        )
        score += min(6.0, richness * 0.75)

        for channel, field_specs in self._SCORING_FIELDS.items():
            values = unique_phrases([query.free_text]) if channel == "free_text" else list(getattr(query, channel))
            for phrase in values:
                possible_weight += max(spec[1] for spec in field_specs)
                best_similarity = 0.0
                best_weight = 0.0
                best_label = ""
                for field_name, weight, label in field_specs:
                    similarity = phrase_similarity(phrase, row[field_name])
                    contribution = similarity * weight
                    if contribution > best_similarity * best_weight:
                        best_similarity = similarity
                        best_weight = weight
                        best_label = label
                if best_similarity >= 0.5:
                    contribution = best_similarity * best_weight
                    score += contribution
                    matched_weight += contribution
                    matched_terms[channel].append(phrase)
                    reasons.append(f"{best_label}命中：{phrase}")

        coverage = round(100 * matched_weight / possible_weight) if possible_weight else 0
        fields = {
            "方源": row["source_text"],
            "组成": row["composition"],
            "用法": row["usage_text"],
            "功用": row["actions"],
            "主治": row["indications"],
            "加减": row["modifications"],
            "宜忌": row["cautions"],
            "正文及其他": row["other_text"],
        }
        fields = {key: value for key, value in fields.items() if value}
        field_limits = {
            "方源": 600,
            "组成": 2500,
            "用法": 1500,
            "功用": 2000,
            "主治": 4000,
            "加减": 3000,
            "宜忌": 1500,
            "正文及其他": 2500,
        }
        truncated_fields = [
            key for key, value in fields.items() if not full_fields and len(value) > field_limits[key]
        ]
        fields = {
            key: value
            if full_fields or len(value) <= field_limits[key]
            else value[: field_limits[key]].rstrip() + "……"
            for key, value in fields.items()
        }
        pdf_pages = json.loads(row["pdf_pages"])
        book_pages = json.loads(row["book_pages"])
        source = {
            "volume": row["source_volume"],
            "pdf_pages": pdf_pages,
            "book_pages": book_pages,
            "citation": self._citation(row["source_volume"], pdf_pages, book_pages),
        }
        return {
            "id": row["id"],
            "name": row["name"],
            "retrieval_score": round(score, 4),
            "evidence_coverage": max(0, min(100, coverage)),
            "match_reasons": list(dict.fromkeys(reasons))[:12],
            "matched_terms": dict(matched_terms),
            "syndrome_index_hits": state.syndrome_hits[:8],
            "fields": fields,
            "truncated_fields": truncated_fields,
            "source": source,
            "quality_flags": json.loads(row["quality_flags"]),
            "_score": score,
        }

    @staticmethod
    def _citation(volume: int | None, pdf_pages: list, book_pages: list) -> str:
        parts = [f"《中医方剂大辞典》第{volume}册" if volume else "《中医方剂大辞典》"]
        if pdf_pages:
            parts.append(f"PDF第{'、'.join(map(str, pdf_pages))}页")
        if book_pages:
            parts.append(f"书内第{'、'.join(map(str, book_pages))}页")
        return "，".join(parts)

    @staticmethod
    def _diversify(ranked: list[dict], top_k: int) -> list[dict]:
        selected: list[dict] = []
        seen_names: set[str] = set()
        for candidate in ranked:
            normalized_name = normalize_text(candidate["name"])
            if normalized_name in seen_names:
                continue
            selected.append(candidate)
            seen_names.add(normalized_name)
            if len(selected) == top_k:
                break
        return selected
