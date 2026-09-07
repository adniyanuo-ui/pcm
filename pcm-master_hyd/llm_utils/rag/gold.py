"""核心方清单的确定性构建与只读加载。

核心方清单只保存辞典条目 ID 和机器初筛的治疗原型标签。方剂事实不复制到清单，
运行时始终从当前 RAG 索引读取。这样可以审计原文，也不会把自动归类误当成新事实。
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from .retriever import FormulaRetriever
from .text import normalize_text


REVIEW_STATUS = "machine_seeded_pending_clinical_review"
GOLD_SCHEMA_VERSION = "1"
_NON_CLASSIC_NAME = re.compile(r"(?:[一二三四五六七八九十\d]+号|自拟|经验|协定|医院)")
_NON_CLASSIC_SOURCE = re.compile(
    r"(?:中药制剂手册|全国中药成药处方集|临床经验|医院|研究所|医药杂志|中医杂志|通讯)"
)
_TEXTBOOK_REFERENCE = re.compile(
    r"《(?:中医)?方剂学(?:讲义|临床手册)?》|《方剂学》|《中医方剂选讲》|"
    r"《中医方剂临床手册》|《中国医学百科全书[·•]方剂学》"
)
_STANDARD_REFERENCE = re.compile(r"《中国药典》|《中医大辞典[·•]方剂分册》")
_CITED_WORK = re.compile(r"《([^》]{2,40})》")

# 仅用于同名异方消歧。若当前索引没有这个出处的合格条目，则宁可不进入 Gold，
# 也不以另一个同名方替代。官方第一批目录中的 100 方由数据文件提供出处。
PREFERRED_PARENT_SOURCES = {
    "桂枝汤": "伤寒论", "白虎汤": "伤寒论", "大承气汤": "伤寒论",
    "调胃承气汤": "伤寒论", "小柴胡汤": "伤寒论", "四逆汤": "伤寒论",
    "通脉四逆汤": "伤寒论", "小建中汤": "伤寒论", "乌梅丸": "伤寒论",
    "麻子仁丸": "伤寒论", "理中丸": "伤寒论", "肾气丸": "金匮",
    "苓甘五味姜辛汤": "金匮", "射干麻黄汤": "金匮", "十枣汤": "伤寒论",
    "防己黄芪汤": "金匮", "酸枣仁汤": "金匮", "黄土汤": "金匮",
    "四君子汤": "鸡峰", "二陈汤": "局方", "逍遥散": "局方",
    "补中益气汤": "内外伤辨", "清胃散": "脾胃论", "玉屏风散": "究原方",
    "四物汤": "理伤续断方", "归脾汤": "济生", "八珍汤": "瑞竹堂",
    "十全大补汤": "局方", "六味地黄丸": "小儿药证直诀", "知柏地黄丸": "医宗金鉴",
    "大补阴丸": "丹溪心法", "左归丸": "景岳全书", "右归丸": "景岳全书",
    "柴胡疏肝散": "统旨", "血府逐瘀汤": "医林改错", "补阳还五汤": "医林改错",
    "少腹逐瘀汤": "医林改错", "清营汤": "温病条辨", "银翘散": "温病条辨",
    "桑菊饮": "温病条辨", "三仁汤": "温病条辨", "增液汤": "温病条辨",
    "安宫牛黄丸": "温病条辨", "大定风珠": "温病条辨", "参苓白术散": "局方",
    "六君子汤": "医学正传", "五苓散": "伤寒论", "茵陈蒿汤": "伤寒论",
    "小陷胸汤": "伤寒论", "大黄附子汤": "金匮", "半夏白术天麻汤": "脾胃论",
}


@dataclass(frozen=True)
class TreatmentPrototype:
    id: str
    name: str
    treatment_terms: tuple[str, ...]
    mechanism_terms: tuple[str, ...]
    direction: str
    strategy: str
    parent_formulas: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "treatment_terms": list(self.treatment_terms),
            "mechanism_terms": list(self.mechanism_terms),
            "direction": self.direction,
            "strategy": self.strategy,
            "parent_formulas": list(self.parent_formulas),
        }


class TreatmentPrototypeCatalog:
    def __init__(self, path: Path):
        self.path = Path(path)
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not 40 <= len(data) <= 100:
            raise ValueError("治疗原型须为 40—100 个")
        prototypes = []
        for item in data:
            prototype = TreatmentPrototype(
                id=str(item["id"]),
                name=str(item["name"]),
                treatment_terms=tuple(str(value) for value in item["treatment_terms"]),
                mechanism_terms=tuple(str(value) for value in item["mechanism_terms"]),
                direction=str(item["direction"]),
                strategy=str(item["strategy"]),
                parent_formulas=tuple(str(value) for value in item["parent_formulas"]),
            )
            prototypes.append(prototype)
        if len({item.id for item in prototypes}) != len(prototypes):
            raise ValueError("治疗原型 id 不能重复")
        self.prototypes = tuple(prototypes)
        self.by_id = {item.id: item for item in prototypes}

    @staticmethod
    def _contains(term: str, text: str) -> bool:
        term, text = normalize_text(term), normalize_text(text)
        # 只接受标签完整出现在辞典原文中；不能因“益气”是“益气活血”的子串，
        # 就把仅写益气的方自动归入益气活血类。
        return bool(term and text and term in text)

    def classify(self, name: str, actions: str, indications: str) -> list[dict]:
        """返回带原文命中依据的机器初筛结果，不宣称专家审定。"""
        normalized_name = normalize_text(name)
        matches = []
        for prototype in self.prototypes:
            treatment_hits = [
                term for term in prototype.treatment_terms if self._contains(term, actions)
            ]
            mechanism_hits = [
                term for term in prototype.mechanism_terms if self._contains(term, indications)
            ]
            parent_hit = any(
                normalize_text(parent) == normalized_name for parent in prototype.parent_formulas
            )
            score = len(treatment_hits) * 8 + len(mechanism_hits) * 3 + (30 if parent_hit else 0)
            if score:
                matches.append(
                    {
                        "id": prototype.id,
                        "score": score,
                        "parent_hit": parent_hit,
                        "treatment_hits": treatment_hits,
                        "mechanism_hits": mechanism_hits,
                    }
                )
        matches.sort(key=lambda item: (-item["score"], item["id"]))
        return matches[:4]


class GoldFormulaSet:
    def __init__(self, manifest_path: Path, metadata_path: Path, catalog: TreatmentPrototypeCatalog):
        self.manifest_path = Path(manifest_path)
        self.metadata_path = Path(metadata_path)
        self.catalog = catalog
        self.records: tuple[dict, ...] = ()
        self.metadata: dict = {}
        if self.manifest_path.is_file() and self.metadata_path.is_file():
            records = []
            with self.manifest_path.open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        records.append(json.loads(line))
            self.records = tuple(records)
            self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self.by_id = {str(record["id"]): record for record in self.records}

    @property
    def ready(self) -> bool:
        return bool(
            300 <= len(self.records) <= 500
            and len(self.by_id) == len(self.records)
            and len({normalize_text(record.get("name")) for record in self.records})
            == len(self.records)
            and all(
                set(record.get("prototype_ids") or []) <= set(self.catalog.by_id)
                for record in self.records
            )
        )

    def compatible_with(self, index_metadata: dict) -> bool:
        return bool(
            self.ready
            and self.metadata.get("schema_version") == GOLD_SCHEMA_VERSION
            and self.metadata.get("formula_count") == len(self.records)
            and self.metadata.get("prototype_count") == len(self.catalog.prototypes)
            and self.metadata.get("index_corpus_sha256")
            == index_metadata.get("corpus_sha256")
        )

    def records_for_prototypes(self, prototype_ids: set[str]) -> list[dict]:
        return [
            record
            for record in self.records
            if prototype_ids.intersection(record.get("prototype_ids") or [])
        ]


def _read_official_names(path: Path) -> tuple[list[str], dict[str, str], dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    expected_sources = {
        normalize_text(name): normalize_text(source)
        for name, source in (data.get("expected_sources") or {}).items()
    }
    return [str(value) for value in data["formula_names"]], expected_sources, {
        "catalog": data.get("catalog", ""),
        "issuing_authority": data.get("issuing_authority", ""),
        "source_url": data.get("source_url", ""),
    }


def _record_quality(row: sqlite3.Row) -> tuple:
    fields = ("source_text", "composition", "actions", "indications", "usage_text", "cautions")
    complete = sum(bool(row[field].strip()) for field in fields)
    pages = bool(json.loads(row["pdf_pages"])) + bool(json.loads(row["book_pages"]))
    return complete, pages, -len(row["id"]), row["id"]


def _authority_quality(row: sqlite3.Row) -> tuple[int, ...]:
    """以本地辞典已有的教材/规范引用和论证丰富度作为机器初筛依据。"""
    evidence = "\n".join(
        [row["actions"], row["indications"], row["cautions"], row["other_text"]]
    )
    cited_works = set(_CITED_WORK.findall(evidence))
    return (
        int(bool(_TEXTBOOK_REFERENCE.search(evidence))),
        int(bool(_STANDARD_REFERENCE.search(evidence))),
        min(len(cited_works), 40),
        int("方论选录" in row["other_text"]),
        int(bool(row["cautions"].strip())),
        int("临证举例" in row["other_text"]),
    )


def build_gold_formula_set(
    *,
    index_path: Path,
    prototype_path: Path,
    official_candidates_path: Path,
    output_path: Path,
    metadata_path: Path,
    target_size: int = 400,
) -> dict:
    """从现有索引选择 300—500 条事实完整且可定位的代表记录。"""
    if not 300 <= target_size <= 500:
        raise ValueError("核心方规模必须在 300—500 之间")
    catalog = TreatmentPrototypeCatalog(prototype_path)
    official_names, official_expected_sources, official_catalog_source = _read_official_names(
        official_candidates_path
    )
    retriever = FormulaRetriever(index_path)
    index_metadata = retriever.metadata()

    uri = f"file:{quote(str(Path(index_path).resolve()))}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT * FROM formulas ORDER BY id").fetchall()
    finally:
        connection.close()

    all_name_counts = Counter(normalize_text(row["name"]) for row in rows)
    by_name: defaultdict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        # Gold 首期只接纳事实链和页码齐全、且无质量标记的条目。
        if not all(row[field].strip() for field in ("source_text", "composition", "actions", "indications")):
            continue
        if not row["source_volume"] or not json.loads(row["pdf_pages"]) or not json.loads(row["book_pages"]):
            continue
        if json.loads(row["quality_flags"]):
            continue
        if _NON_CLASSIC_NAME.search(row["name"]) or _NON_CLASSIC_SOURCE.search(row["source_text"]):
            continue
        by_name[normalize_text(row["name"])].append(row)

    candidates = []
    official_lookup = {normalize_text(name): position for position, name in enumerate(official_names)}
    parent_expected_sources = {
        normalize_text(name): normalize_text(source)
        for name, source in PREFERRED_PARENT_SOURCES.items()
    }
    for normalized_name, same_name_rows in by_name.items():
        expected_official_source = official_expected_sources.get(normalized_name, "")
        parent_source = parent_expected_sources.get(normalized_name, "")
        official_source_rows = [
            row
            for row in same_name_rows
            if expected_official_source
            and expected_official_source in normalize_text(row["source_text"])
        ]
        parent_source_rows = [
            row
            for row in same_name_rows
            if parent_source and parent_source in normalize_text(row["source_text"])
        ]
        if official_source_rows:
            row = max(official_source_rows, key=_record_quality)
        elif parent_source_rows:
            # 官方目录版本缺少完整功用等字段时，可收入明确的母方版本，但不标为官方目录条目。
            row = max(parent_source_rows, key=_record_quality)
        elif expected_official_source or parent_source:
            # 已知应指向某一出处时，不以无关的同名方替代。
            continue
        else:
            row = max(same_name_rows, key=_record_quality)
        classified = catalog.classify(row["name"], row["actions"], row["indications"])
        if not classified:
            continue
        is_official = normalized_name in official_lookup and bool(official_source_rows)
        is_parent = any(item["parent_hit"] for item in classified)
        candidates.append(
            {
                "row": row,
                "classified": classified,
                "same_name_record_count": all_name_counts[normalized_name],
                "official_position": official_lookup.get(normalized_name),
                "is_official": is_official,
                "is_parent": is_parent,
                "quality": _record_quality(row),
                "authority_quality": _authority_quality(row),
            }
        )

    selected: list[dict] = []
    selected_names: set[str] = set()

    def add(candidate: dict, source: str) -> bool:
        name_key = normalize_text(candidate["row"]["name"])
        if name_key in selected_names or len(selected) >= target_size:
            return False
        row, classified = candidate["row"], candidate["classified"]
        selected.append(
            {
                "id": str(row["id"]),
                "name": str(row["name"]),
                "primary_prototype_id": classified[0]["id"],
                "prototype_ids": [item["id"] for item in classified],
                "classification_evidence": [
                    {
                        "prototype_id": item["id"],
                        "parent_formula_match": item["parent_hit"],
                        "treatment_terms_in_dictionary_actions": item["treatment_hits"],
                        "mechanism_terms_in_dictionary_indications": item["mechanism_hits"],
                    }
                    for item in classified
                ],
                "selection_source": source,
                "same_name_record_count": candidate["same_name_record_count"],
                "review_status": REVIEW_STATUS,
                "clinical_reviewed": False,
            }
        )
        selected_names.add(name_key)
        return True

    official_candidates = sorted(
        (item for item in candidates if item["is_official"]),
        key=lambda item: item["official_position"],
    )
    for candidate in official_candidates:
        add(candidate, "official_catalog_candidate")

    parent_candidates = sorted(
        (item for item in candidates if item["is_parent"]),
        key=lambda item: (
            *(-value for value in item["authority_quality"]),
            -item["classified"][0]["score"],
            normalize_text(item["row"]["name"]),
        ),
    )
    for candidate in parent_candidates:
        add(candidate, "prototype_parent_formula")

    by_prototype: defaultdict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        for match in candidate["classified"]:
            by_prototype[match["id"]].append(candidate)
    for values in by_prototype.values():
        values.sort(
            key=lambda item: (
                *(-value for value in item["authority_quality"]),
                -max(match["score"] for match in item["classified"]),
                -item["quality"][0],
                -item["quality"][1],
                normalize_text(item["row"]["name"]),
            )
        )

    # 先确保每个治疗原型至少有一个可追溯候选；随后按教材/规范引用和方论丰富度
    # 全局补齐。不能用按方族机械轮询的方式，把资料完整但临床代表性弱的生僻方
    # 大量包装成“核心方”。
    represented = {
        prototype_id for item in selected for prototype_id in item["prototype_ids"]
    }
    for prototype in catalog.prototypes:
        if prototype.id in represented:
            continue
        for candidate in by_prototype.get(prototype.id, []):
            if add(candidate, "prototype_coverage_seed"):
                represented.update(selected[-1]["prototype_ids"])
                break

    ranked_candidates = sorted(
        candidates,
        key=lambda item: (
            *(-value for value in item["authority_quality"]),
            -max(match["score"] for match in item["classified"]),
            -item["quality"][0],
            -item["quality"][1],
            normalize_text(item["row"]["name"]),
        ),
    )
    for candidate in ranked_candidates:
        if len(selected) >= target_size:
            break
        add(candidate, "authority_ranked_dictionary_seed")

    if len(selected) < target_size:
        raise RuntimeError(f"仅找到 {len(selected)} 首满足门禁的核心方，未达到 {target_size} 首")

    output_path, metadata_path = Path(output_path), Path(metadata_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in selected)
    temporary_output = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp")
    temporary_output.write_text(lines, encoding="utf-8")
    temporary_output.replace(output_path)

    primary_distribution = Counter(item["primary_prototype_id"] for item in selected)
    represented_prototypes = {
        prototype_id for item in selected for prototype_id in item["prototype_ids"]
    }
    metadata = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "target_size": target_size,
        "formula_count": len(selected),
        "prototype_count": len(catalog.prototypes),
        "represented_prototype_count": len(represented_prototypes),
        "primary_represented_prototype_count": len(primary_distribution),
        "primary_prototype_distribution": dict(sorted(primary_distribution.items())),
        "official_candidates_requested": len(official_names),
        "official_candidates_selected": sum(
            item["selection_source"] == "official_catalog_candidate" for item in selected
        ),
        "official_source": official_catalog_source,
        "index_corpus_sha256": index_metadata.get("corpus_sha256"),
        "selection_policy": {
            "required_dictionary_fields": ["方源", "组成", "功用", "主治"],
            "required_location": ["册数", "PDF页码", "书内页码"],
            "quality_flags_allowed": False,
            "facts_source": "runtime_read_from_dictionary_index_by_id",
            "classification": REVIEW_STATUS,
            "same_name_policy": "known_source_must_match_or_formula_is_excluded",
            "completion_policy": (
                "official_and_parent_formulas_first_then_prototype_coverage_then_"
                "textbook_standard_and_commentary_evidence"
            ),
        },
    }
    temporary_metadata = metadata_path.with_name(f".{metadata_path.name}.{os.getpid()}.tmp")
    temporary_metadata.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_metadata.replace(metadata_path)
    return metadata
