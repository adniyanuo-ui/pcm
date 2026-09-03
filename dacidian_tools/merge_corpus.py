#!/usr/bin/env python3
"""Validate and merge volumes 1-10 into one auditable formula corpus."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
OUTPUT = ROOT / "dacidian_text" / "corpus"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    configs = [
        row
        for row in json.loads((TOOLS / "volumes.json").read_text(encoding="utf-8"))
        if row["kind"] == "dictionary"
    ]
    configs.sort(key=lambda row: row["volume"])
    all_entries: list[dict] = []
    all_reviews: list[dict] = []
    unresolved_headers: list[dict] = []
    volume_summaries: list[dict] = []
    aggregate_fields: collections.Counter = collections.Counter()
    aggregate_flags: collections.Counter = collections.Counter()

    expected_id = 1
    for config in configs:
        volume = config["volume"]
        prefix = f"volume_{volume:02d}"
        volume_dir = ROOT / "dacidian_text" / prefix
        quality = json.loads((volume_dir / f"{prefix}_quality.json").read_text(encoding="utf-8"))
        if quality["missing_entry_ids_count"] or quality["duplicate_entry_ids"] or quality["non_monotonic_pairs"]:
            raise RuntimeError(f"Volume {volume} has unresolved identifier errors")
        entries = load_jsonl(volume_dir / f"{prefix}_entries.jsonl")
        actual_ids = [int(entry["id"]) for entry in entries]
        configured_ids = list(range(config["first_entry_id"], config["last_entry_id"] + 1))
        if actual_ids != configured_ids:
            raise RuntimeError(f"Volume {volume} entries do not match its configured continuous range")
        if actual_ids[0] != expected_id:
            raise RuntimeError(f"Cross-volume gap before volume {volume}: expected {expected_id}")
        expected_id = actual_ids[-1] + 1

        for entry in entries:
            aggregate_fields.update(entry["fields"].keys())
            aggregate_flags.update(entry.get("quality_flags", []))
        all_entries.extend(entries)

        review_path = volume_dir / f"{prefix}_needs_review.jsonl"
        if review_path.exists():
            for row in load_jsonl(review_path):
                all_reviews.append({"volume": volume, **row})
        audit_path = volume_dir / f"{prefix}_header_audit.jsonl"
        if audit_path.exists():
            for row in load_jsonl(audit_path):
                if row.get("status") in {"unresolved_three_way_disagreement", "raw_header_box_not_found"}:
                    unresolved_headers.append({"volume": volume, **row})

        normalization = quality.get("field_label_normalization", {})
        volume_summaries.append(
            {
                "volume": volume,
                "entry_range": [config["first_entry_id"], config["last_entry_id"]],
                "entries": len(entries),
                "raw_lines": quality["raw_line_count"],
                "raw_confidence_mean": quality["raw_line_confidence"]["mean"],
                "raw_lines_below_0_70": quality["raw_line_confidence"]["below_0_70"],
                "header_corrections": normalization.get("header_correction", 0),
                "sequence_corrections": normalization.get("header_sequence_correction", 0),
                "name_corrections": normalization.get("name_correction", 0),
                "source_page_missing_placeholders": normalization.get("source_page_missing_placeholder", 0),
                "partial_source_page_missing": normalization.get("partial_source_page_missing", 0),
            }
        )

    if expected_id != 96593 or len(all_entries) != 96592:
        raise RuntimeError(f"Unexpected global corpus end/count: next={expected_id}, count={len(all_entries)}")

    exclusions = [entry for entry in all_entries if entry.get("record_status", "complete") != "complete"]
    status_counts = collections.Counter(entry["record_status"] for entry in exclusions)
    blank_pages = sorted(
        {
            (entry["source"]["volume"], page)
            for entry in exclusions
            if entry["record_status"] == "source_page_missing"
            for page in entry["source"]["pdf_pages"]
        }
    )

    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries_path = OUTPUT / "fangji_entries.jsonl"
    exclusions_path = OUTPUT / "rag_exclusions.jsonl"
    review_path = OUTPUT / "review_index.jsonl"
    unresolved_path = OUTPUT / "unresolved_header_audit.jsonl"
    write_jsonl(entries_path, all_entries)
    write_jsonl(exclusions_path, exclusions)
    write_jsonl(review_path, all_reviews)
    write_jsonl(unresolved_path, unresolved_headers)

    total_raw_lines = sum(item["raw_lines"] for item in volume_summaries)
    weighted_confidence = sum(
        item["raw_lines"] * item["raw_confidence_mean"] for item in volume_summaries
    ) / total_raw_lines
    summary = {
        "corpus": "中医方剂大辞典正编第1-10册",
        "entry_id_range": [1, 96592],
        "total_entries": len(all_entries),
        "rag_ready_entries": len(all_entries) - len(exclusions),
        "rag_excluded_entries": len(exclusions),
        "rag_excluded_status_counts": dict(status_counts),
        "source_pdf_blank_pages": [
            {"volume": volume, "pdf_page": page} for volume, page in blank_pages
        ],
        "raw_line_count": total_raw_lines,
        "raw_line_confidence_weighted_mean": round(weighted_confidence, 6),
        "raw_lines_below_0_70": sum(item["raw_lines_below_0_70"] for item in volume_summaries),
        "review_index_records": len(all_reviews),
        "unresolved_header_audit_records": len(unresolved_headers),
        "field_counts": dict(aggregate_fields.most_common()),
        "quality_flag_counts": dict(aggregate_flags.most_common()),
        "volumes": volume_summaries,
        "outputs": {
            "entries": entries_path.name,
            "rag_exclusions": exclusions_path.name,
            "review_index": review_path.name,
            "unresolved_header_audit": unresolved_path.name,
        },
    }
    summary["output_sha256"] = {
        "entries": sha256_file(entries_path),
        "rag_exclusions": sha256_file(exclusions_path),
        "review_index": sha256_file(review_path),
        "unresolved_header_audit": sha256_file(unresolved_path),
    }
    summary_path = OUTPUT / "quality_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    readme = f"""# 《中医方剂大辞典》正编合并语料

本目录由 `dacidian_tools/merge_corpus.py` 从第 1—10 册确定性生成。

- `fangji_entries.jsonl`：方号 `00001—96592` 的全部 {len(all_entries)} 条记录；
- `rag_exclusions.jsonl`：因源 PDF 全白页或正文部分缺失而禁止进入 RAG 的 {len(exclusions)} 条记录；
- `review_index.jsonl`：各册质量标记的合并索引，可按卷号和 PDF 页回查；
- `unresolved_header_audit.jsonl`：正文、目录和中型 OCR 尚未达成一致的方名疑点；
- `quality_summary.json`：全书统计、空白页清单及输出 SHA-256。

构建 RAG 时，必须排除 `record_status` 不为 `complete` 的记录。当前可入库 {len(all_entries) - len(exclusions)} 条，排除 {len(exclusions)} 条。未经复核不得用目录或模型猜测补写缺页正文。
"""
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
