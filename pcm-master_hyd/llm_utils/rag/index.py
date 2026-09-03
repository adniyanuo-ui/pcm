import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .text import indexed_text


SCHEMA_VERSION = "1"
RAG_READY_STATUS = "complete"

INDEXED_FIELDS = {
    "source_text": ("方源",),
    "composition": ("组成",),
    "usage_text": ("用法", "制法"),
    "actions": ("功用",),
    "indications": ("主治",),
    "modifications": ("加减", "附方"),
    "cautions": ("宜忌",),
}


def _join_fields(fields: dict, names: tuple[str, ...]) -> str:
    return "\n".join(str(fields.get(name, "")).strip() for name in names if fields.get(name))


def _other_fields(fields: dict) -> str:
    consumed = {name for names in INDEXED_FIELDS.values() for name in names}
    return "\n".join(
        f"{name}：{value}" for name, value in fields.items() if name not in consumed and value
    )


class FormulaIndexBuilder:
    """将经过质量门禁的 JSONL 语料构建成 SQLite FTS5 索引。"""

    def __init__(self, corpus: Path, syndrome_index: Path | None, output: Path):
        self.corpus = Path(corpus)
        self.syndrome_index = Path(syndrome_index) if syndrome_index else None
        self.output = Path(output)

    def build(self) -> dict:
        if not self.corpus.is_file():
            raise FileNotFoundError(f"找不到方剂语料：{self.corpus}")
        if self.syndrome_index and not self.syndrome_index.is_file():
            raise FileNotFoundError(f"找不到病证索引：{self.syndrome_index}")

        self.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.output.with_name(f".{self.output.name}.{os.getpid()}.tmp")
        if temporary.exists():
            temporary.unlink()

        stats = {
            "total_records": 0,
            "indexed_records": 0,
            "excluded_records": 0,
            "syndrome_terms": 0,
            "syndrome_links": 0,
        }
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(temporary)
            self._create_schema(connection)
            self._load_formulas(connection, stats)
            if self.syndrome_index:
                self._load_syndromes(connection, stats)
            metadata = self._write_metadata(connection, stats)
            connection.commit()
            connection.execute("PRAGMA optimize")
            connection.close()
            connection = None
            temporary.replace(self.output)
            return metadata
        except Exception:
            if connection is not None:
                connection.close()
            if temporary.exists():
                temporary.unlink()
            raise

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            PRAGMA temp_store=MEMORY;
            PRAGMA cache_size=-131072;

            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE formulas (
                rowid INTEGER PRIMARY KEY,
                id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                source_text TEXT NOT NULL,
                composition TEXT NOT NULL,
                usage_text TEXT NOT NULL,
                actions TEXT NOT NULL,
                indications TEXT NOT NULL,
                modifications TEXT NOT NULL,
                cautions TEXT NOT NULL,
                other_text TEXT NOT NULL,
                source_volume INTEGER,
                pdf_pages TEXT NOT NULL,
                book_pages TEXT NOT NULL,
                quality_flags TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE formula_fts USING fts5(
                name_terms,
                action_terms,
                indication_terms,
                composition_terms,
                modification_terms,
                all_terms,
                content='',
                tokenize='unicode61 remove_diacritics 2'
            );

            CREATE TABLE syndrome_terms (
                id INTEGER PRIMARY KEY,
                term TEXT NOT NULL,
                major_category TEXT NOT NULL,
                minor_category TEXT NOT NULL,
                pdf_pages TEXT NOT NULL,
                book_pages TEXT NOT NULL
            );

            CREATE TABLE syndrome_links (
                syndrome_id INTEGER NOT NULL,
                formula_id TEXT NOT NULL,
                PRIMARY KEY (syndrome_id, formula_id)
            ) WITHOUT ROWID;

            CREATE INDEX syndrome_terms_term_idx ON syndrome_terms(term);
            CREATE INDEX syndrome_links_formula_idx ON syndrome_links(formula_id);
            """
        )

    def _load_formulas(self, connection: sqlite3.Connection, stats: dict) -> None:
        formula_sql = """
            INSERT INTO formulas(
                id, name, source_text, composition, usage_text, actions, indications,
                modifications, cautions, other_text, source_volume, pdf_pages,
                book_pages, quality_flags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        fts_sql = """
            INSERT INTO formula_fts(
                rowid, name_terms, action_terms, indication_terms, composition_terms,
                modification_terms, all_terms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        digest = hashlib.sha256()
        with self.corpus.open("rb") as binary_stream:
            for raw_line in binary_stream:
                digest.update(raw_line)
                stats["total_records"] += 1
                record = json.loads(raw_line)
                if record.get("record_status", RAG_READY_STATUS) != RAG_READY_STATUS:
                    stats["excluded_records"] += 1
                    continue

                fields = record.get("fields") or {}
                values = {
                    key: _join_fields(fields, names) for key, names in INDEXED_FIELDS.items()
                }
                values["other_text"] = _other_fields(fields)
                source = record.get("source") or {}
                cursor = connection.execute(
                    formula_sql,
                    (
                        str(record["id"]),
                        str(record.get("name", "")),
                        values["source_text"],
                        values["composition"],
                        values["usage_text"],
                        values["actions"],
                        values["indications"],
                        values["modifications"],
                        values["cautions"],
                        values["other_text"],
                        source.get("volume"),
                        json.dumps(source.get("pdf_pages") or [], ensure_ascii=False),
                        json.dumps(source.get("book_pages") or [], ensure_ascii=False),
                        json.dumps(record.get("quality_flags") or [], ensure_ascii=False),
                    ),
                )
                rowid = cursor.lastrowid
                all_values = [record.get("name", ""), *values.values()]
                connection.execute(
                    fts_sql,
                    (
                        rowid,
                        indexed_text(record.get("name", "")),
                        indexed_text(values["actions"]),
                        indexed_text(values["indications"]),
                        indexed_text(values["composition"]),
                        indexed_text(values["modifications"]),
                        indexed_text(*all_values),
                    ),
                )
                stats["indexed_records"] += 1
                if stats["indexed_records"] % 5000 == 0:
                    connection.commit()
        stats["corpus_sha256"] = digest.hexdigest()

    def _load_syndromes(self, connection: sqlite3.Connection, stats: dict) -> None:
        assert self.syndrome_index is not None
        formula_ids = {row[0] for row in connection.execute("SELECT id FROM formulas")}
        with self.syndrome_index.open(encoding="utf-8") as stream:
            for line in stream:
                record = json.loads(line)
                category = record.get("category") or {}
                source = record.get("source") or {}
                cursor = connection.execute(
                    """
                    INSERT INTO syndrome_terms(
                        term, major_category, minor_category, pdf_pages, book_pages
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(record.get("term", "")),
                        str(category.get("major", "")),
                        str(category.get("minor", "")),
                        json.dumps(source.get("pdf_pages") or [], ensure_ascii=False),
                        json.dumps(source.get("book_pages") or [], ensure_ascii=False),
                    ),
                )
                syndrome_id = cursor.lastrowid
                links = [
                    (syndrome_id, str(entry_id))
                    for entry_id in record.get("entry_ids") or []
                    if str(entry_id) in formula_ids
                ]
                connection.executemany(
                    "INSERT INTO syndrome_links(syndrome_id, formula_id) VALUES (?, ?)", links
                )
                stats["syndrome_terms"] += 1
                stats["syndrome_links"] += len(links)

    def _write_metadata(self, connection: sqlite3.Connection, stats: dict) -> dict:
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "corpus_path": str(self.corpus.resolve()),
            "syndrome_index_path": str(self.syndrome_index.resolve())
            if self.syndrome_index
            else "",
            **stats,
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            [(key, json.dumps(value, ensure_ascii=False)) for key, value in metadata.items()],
        )
        return metadata
