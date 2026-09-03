#!/usr/bin/env python3
"""Create loss-preserving cleaned text and structured entries from raw OCR."""

from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import re
import statistics
import unicodedata
from pathlib import Path
from typing import Any, Iterable


KNOWN_FIELDS = (
    "方源",
    "异名",
    "组成",
    "制法",
    "用法",
    "功用",
    "主治",
    "宜忌",
    "加减",
    "附方",
    "方论选录",
    "临证举例",
    "现代研究",
    "备考",
    "备注",
)
VOLUME_01_MAX_ENTRY_ID = 9634

FIELD_ALIASES = {
    "来源": "方源",
    "方原": "方源",
    "组咸": "组成",
    "主洽": "主治",
    "主冶": "主治",
    "功效": "功用",
    "禁忌": "宜忌",
    "方论选绿": "方论选录",
    "临证举列": "临证举例",
}

ID_TRANSLATION = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"})
ENTRY_RE = re.compile(r"^\s*([0-9OoIl]{5})\s*([^\d].*?)?\s*$")
FIELD_RE = re.compile(r"^[\[【〔(（]\s*([^\]】〕)）]{1,8})\s*[\]】〕)）]\s*(.*)$")
TOC_RE = re.compile(r"^\s*([0-9OoIl]{5})\s*(.+?)\s*[.·…]{2,}\s*(\d{1,4})\s*$")
TOC_FALLBACK_RE = re.compile(r"^\s*([0-9OoIl]{5})\s*(.+?)\s+(\d{1,4})\s*$")
TOC_NAME_ONLY_RE = re.compile(r"^\s*([0-9OoIl]{5})\s*(\D.+?)\s*[.·…]*\s*$")
TOC_DIRECT_NAME_RE = re.compile(r"^\s*([0-9OoIl]{5})\s*(\D.*?)(?:\s*[.·…]{2,}.*)?\s*$")
FIELD_NAMES_RE = "|".join(sorted((*KNOWN_FIELDS, *FIELD_ALIASES), key=len, reverse=True))
RUNNING_HEADER_FRAGMENT_RE = re.compile(
    r"^[0-9A-Za-z/=<>@()（）\s一二三四五六七八九十画总页第上下入大万寸山干土千川久卫小飞马儿元刀回国了]+$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_space(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u3000", " ").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def normalize_id(raw: str) -> str:
    return raw.translate(ID_TRANSLATION)


def normalize_field_label(raw: str) -> tuple[str | None, str]:
    compact = re.sub(r"\s+", "", raw)
    if compact in KNOWN_FIELDS:
        return compact, "exact"
    if compact in FIELD_ALIASES:
        return FIELD_ALIASES[compact], "alias"
    match = difflib.get_close_matches(compact, KNOWN_FIELDS, n=1, cutoff=0.72)
    if match:
        return match[0], "fuzzy"
    return None, "unknown"


def iter_raw_lines(page_files: Iterable[Path], start: int, end: int) -> Iterable[dict[str, Any]]:
    for path in page_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        page = int(data["pdf_page"])
        if not start <= page <= end:
            continue
        for region_index, region in enumerate(data["regions"]):
            for line_index, line in enumerate(region["lines"]):
                text = normalize_space(line["text"])
                if not text:
                    continue
                min_y = min(point[1] for point in line["box"])
                at_crop_top = min_y <= float(region["crop"][1]) + 2.1
                is_entry_header = bool(ENTRY_RE.match(text))
                if page >= 89 and at_crop_top and not is_entry_header:
                    if "总" in text or (len(text) <= 18 and RUNNING_HEADER_FRAGMENT_RE.fullmatch(text)):
                        # Old running headers sit exactly on the crop boundary.
                        # They may be detected as one string or several short
                        # page/radical fragments.  Raw page JSON remains intact.
                        continue
                yield {
                    "text": text,
                    "confidence": float(line["confidence"]),
                    "pdf_page": page,
                    "book_page": data.get("book_page"),
                    "region": region["name"],
                    "region_index": region_index,
                    "line_index": line_index,
                    "box": line["box"],
                }


def cluster_visual_rows(lines: Iterable[dict[str, Any]], tolerance: float = 13.0) -> list[dict[str, Any]]:
    """Join separately detected ID/name and page-number boxes on a TOC row."""
    groups: dict[tuple[int, str], list[dict[str, Any]]] = collections.defaultdict(list)
    for line in lines:
        groups[(line["pdf_page"], line["region"])].append(line)

    rows: list[dict[str, Any]] = []
    for (pdf_page, region), group in sorted(groups.items()):
        group.sort(key=lambda item: ((item["box"][0][1] + item["box"][2][1]) / 2, item["box"][0][0]))
        clusters: list[list[dict[str, Any]]] = []
        centers: list[float] = []
        for item in group:
            center_y = (item["box"][0][1] + item["box"][2][1]) / 2
            if not clusters or abs(center_y - centers[-1]) > tolerance:
                clusters.append([item])
                centers.append(center_y)
            else:
                clusters[-1].append(item)
                centers[-1] = statistics.fmean(
                    (part["box"][0][1] + part["box"][2][1]) / 2 for part in clusters[-1]
                )
        for cluster in clusters:
            cluster.sort(key=lambda item: item["box"][0][0])
            rows.append(
                {
                    "text": " ".join(item["text"] for item in cluster),
                    "confidence": min(item["confidence"] for item in cluster),
                    "pdf_page": pdf_page,
                    "region": region,
                    "box_count": len(cluster),
                }
            )
    return rows


def parse_toc(lines: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lines = list(lines)
    toc: dict[str, dict[str, Any]] = {}
    # First recover names from individual OCR boxes.  Page numbers are often a
    # separate box, so this pass intentionally leaves book_page unset.
    for line in lines:
        match = TOC_DIRECT_NAME_RE.match(line["text"])
        if not match:
            continue
        entry_id = normalize_id(match.group(1))
        name = match.group(2).strip(" .·…")
        if not entry_id.isdigit() or not name:
            continue
        toc[entry_id] = {
            "id": entry_id,
            "name": name,
            "book_page": None,
            "pdf_page": line["pdf_page"],
            "confidence": line["confidence"],
        }

    # Then join visual rows to attach page numbers where OCR found them.
    for line in cluster_visual_rows(lines):
        text = line["text"]
        match = TOC_RE.match(text) or TOC_FALLBACK_RE.match(text) or TOC_NAME_ONLY_RE.match(text)
        if not match:
            continue
        entry_id = normalize_id(match.group(1))
        name = match.group(2).strip(" .·…")
        if not entry_id.isdigit() or not name:
            continue
        candidate = {
            "id": entry_id,
            "name": name,
            "book_page": int(match.group(3)) if match.lastindex and match.lastindex >= 3 else None,
            "pdf_page": line["pdf_page"],
            "confidence": line["confidence"],
        }
        if (
            entry_id not in toc
            or (candidate["book_page"] is not None and toc[entry_id]["book_page"] is None)
            or candidate["confidence"] > toc[entry_id]["confidence"]
        ):
            toc[entry_id] = candidate
    return toc


def load_header_corrections(path: Path | None) -> dict[tuple[int, str], dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {(int(row["pdf_page"]), normalize_space(row["raw_text"])): row for row in rows}


def load_name_corrections(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["id"]): row for row in rows}


def load_text_corrections(path: Path | None) -> dict[str, list[dict[str, Any]]]:
    if path is None or not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in rows:
        result[str(row["id"])].append(row)
    return dict(result)


def split_embedded_fields(text: str) -> list[str]:
    """Repair obvious OCR bracket variants and split merged field lines."""
    text = re.sub(
        rf"[\[【〔(（]?\s*({FIELD_NAMES_RE})\s*[\]】〕)）]",
        lambda match: f"【{normalize_field_label(match.group(1))[0] or match.group(1)}】",
        text,
    )
    starts = [match.start() for match in re.finditer(rf"【(?:{'|'.join(KNOWN_FIELDS)})】", text)]
    if len(starts) <= 1:
        return [text]
    parts: list[str] = []
    if starts[0] > 0:
        parts.append(text[: starts[0]])
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        parts.append(text[start:end])
    return [part.strip() for part in parts if part.strip()]


def join_field_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    result = lines[0]
    for line in lines[1:]:
        # Preserve explicit spaces recognized inside a line, but remove visual
        # line wrapping between Chinese text lines.
        if result.endswith(("-", "—")):
            result += line
        elif re.search(r"[A-Za-z0-9]$", result) and re.match(r"^[A-Za-z0-9]", line):
            result += " " + line
        else:
            result += line
    return result.strip()


def parse_entries(
    lines: Iterable[dict[str, Any]],
    toc: dict[str, dict[str, Any]],
    corrections: dict[tuple[int, str], dict[str, Any]],
    name_corrections: dict[str, dict[str, Any]],
    text_corrections: dict[str, list[dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], collections.Counter]:
    entries: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    label_stats: collections.Counter = collections.Counter()
    current: dict[str, Any] | None = None
    current_field = "正文"

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        current["fields"] = {key: join_field_lines(value) for key, value in current["fields"].items() if value}
        applied_text_corrections: list[dict[str, Any]] = []
        for correction in text_corrections.get(current["id"], []):
            field = correction["field"]
            source_text = correction["from"]
            target_text = correction["to"]
            value = current["fields"].get(field, "")
            if source_text in value:
                current["fields"][field] = value.replace(source_text, target_text, 1)
                applied_text_corrections.append(
                    {"field": field, "from": source_text, "to": target_text, "note": correction.get("note", "")}
                )
        if applied_text_corrections:
            current["text_corrections"] = applied_text_corrections
            current["quality_flags"].append("text_repaired_from_verified_source")
            label_stats["text_correction"] += len(applied_text_corrections)
        scores = current.pop("_scores")
        current["ocr_confidence"] = {
            "mean": round(statistics.fmean(scores), 6) if scores else None,
            "minimum": round(min(scores), 6) if scores else None,
            "line_count": len(scores),
        }
        source_pages = sorted(set(current.pop("_pages")))
        current["source"] = {
            "volume": 1,
            "pdf_pages": source_pages,
            "book_pages": [page - 88 for page in source_pages],
        }
        toc_item = toc.get(current["id"])
        if toc_item:
            current["toc"] = {"name": toc_item["name"], "book_page": toc_item["book_page"]}
            ratio = difflib.SequenceMatcher(None, current["name"].replace(" ", ""), toc_item["name"].replace(" ", "")).ratio()
            current["name_toc_similarity"] = round(ratio, 4)
            if ratio < 0.70:
                current["quality_flags"].append("name_differs_from_toc")
        else:
            current["quality_flags"].append("missing_from_parsed_toc")
        if current["ocr_confidence"]["minimum"] is not None and current["ocr_confidence"]["minimum"] < 0.70:
            current["quality_flags"].append("low_confidence_line")
        if "方源" not in current["fields"] and "正文" not in current["fields"]:
            current["quality_flags"].append("missing_source_field")
        entries.append(current)
        if current["quality_flags"]:
            issues.append(
                {
                    "id": current["id"],
                    "name": current["name"],
                    "flags": current["quality_flags"],
                    "source": current["source"],
                    "toc": current.get("toc"),
                }
            )
        current = None

    for line in lines:
        raw_text = line["text"]
        correction = corrections.get((line["pdf_page"], raw_text))
        if correction:
            segments = [correction["corrected_header"]]
            if correction.get("keep_raw_after_header"):
                segments.append(raw_text)
        else:
            segments = split_embedded_fields(raw_text)
        for segment_index, text in enumerate(segments):
            if text != raw_text:
                label_stats["embedded_split"] += 1
            entry_match = ENTRY_RE.match(text)
            if entry_match:
                entry_id = normalize_id(entry_match.group(1))
                name = (entry_match.group(2) or "").strip(" -—·.")
                numeric_id = int(entry_id) if entry_id.isdigit() else -1
                # Dictionary entry numbers in this volume are 00001-09634.  This
                # range check prevents page numbers and running headers becoming
                # false entries.
                if 1 <= numeric_id <= VOLUME_01_MAX_ENTRY_ID and name:
                    flush()
                    name_correction = name_corrections.get(entry_id)
                    original_name = name
                    if name_correction and normalize_space(name_correction["from_name"]) == name:
                        name = normalize_space(name_correction["to_name"])
                    current = {
                        "id": entry_id,
                        "name": name,
                        "raw_header": text,
                        "header_confidence": line["confidence"],
                        "fields": collections.OrderedDict(),
                        "quality_flags": [],
                        "_scores": [line["confidence"]],
                        "_pages": [line["pdf_page"]],
                    }
                    if correction and segment_index == 0:
                        current["header_correction"] = {
                            "pdf_page": line["pdf_page"],
                            "raw_text": raw_text,
                            "note": correction.get("note", ""),
                        }
                        current["quality_flags"].append("header_repaired_from_pdf_or_toc")
                        label_stats["header_correction"] += 1
                    if name_correction and name != original_name:
                        current["name_correction"] = {
                            "from": original_name,
                            "to": name,
                            "method": name_correction.get("method", "independent_ocr_consensus"),
                            "medium_ocr": name_correction.get("medium_ocr"),
                            "toc_ocr": name_correction.get("toc_ocr"),
                        }
                        current["quality_flags"].append("name_repaired_by_independent_ocr_consensus")
                        label_stats["name_correction"] += 1
                    current_field = "正文"
                    continue

            if current is None:
                continue

            current["_scores"].append(line["confidence"])
            current["_pages"].append(line["pdf_page"])
            field_match = FIELD_RE.match(text)
            if field_match:
                field, method = normalize_field_label(field_match.group(1))
                if field:
                    current_field = field
                    label_stats[method] += 1
                    rest = field_match.group(2).strip()
                    if rest:
                        current["fields"].setdefault(current_field, []).append(rest)
                    continue
            current["fields"].setdefault(current_field, []).append(text)

    flush()
    return entries, issues, label_stats


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-pages", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--first-content-page", type=int, default=89)
    parser.add_argument("--last-page", type=int, required=True)
    parser.add_argument(
        "--header-corrections",
        type=Path,
        default=Path(__file__).with_name("volume_01_header_corrections.json"),
    )
    parser.add_argument("--name-corrections", type=Path, default=None)
    parser.add_argument(
        "--text-corrections",
        type=Path,
        default=Path(__file__).with_name("volume_01_text_corrections.json"),
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    page_files = sorted(args.raw_pages.glob("page_*.json"))
    front_lines = list(iter_raw_lines(page_files, 1, args.first_content_page - 1))
    toc_lines = [line for line in front_lines if line["pdf_page"] >= 11]
    toc = parse_toc(toc_lines)
    content_lines = list(iter_raw_lines(page_files, args.first_content_page, args.last_page))
    corrections = load_header_corrections(args.header_corrections)
    name_corrections = load_name_corrections(args.name_corrections)
    text_corrections = load_text_corrections(args.text_corrections)
    entries, issues, label_stats = parse_entries(
        content_lines, toc, corrections, name_corrections, text_corrections
    )

    raw_text_path = args.output / "volume_01_raw.txt"
    with raw_text_path.open("w", encoding="utf-8") as handle:
        last_page = None
        for line in content_lines:
            if line["pdf_page"] != last_page:
                handle.write(
                    f"\n===== PDF_PAGE {line['pdf_page']:04d} / BOOK_PAGE {line['book_page']} =====\n"
                )
                last_page = line["pdf_page"]
            handle.write(line["text"] + "\n")

    front_text_path = args.output / "volume_01_front_matter.txt"
    with front_text_path.open("w", encoding="utf-8") as handle:
        last_page = None
        for line in front_lines:
            if line["pdf_page"] != last_page:
                handle.write(f"\n===== PDF_PAGE {line['pdf_page']:04d} =====\n")
                last_page = line["pdf_page"]
            handle.write(line["text"] + "\n")

    clean_text_path = args.output / "volume_01_clean.txt"
    with clean_text_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(f"\n{entry['id']} {entry['name']}\n")
            for field, value in entry["fields"].items():
                handle.write(f"【{field}】{value}\n")
            pages = ",".join(str(p) for p in entry["source"]["book_pages"])
            handle.write(f"【页码】{pages}\n")

    toc_path = args.output / "volume_01_toc_index.jsonl"
    write_jsonl(toc_path, (toc[key] for key in sorted(toc)))
    entries_path = args.output / "volume_01_entries.jsonl"
    write_jsonl(entries_path, entries)
    review_path = args.output / "volume_01_needs_review.jsonl"
    write_jsonl(review_path, issues)
    low_confidence_path = args.output / "volume_01_low_confidence_lines.jsonl"
    write_jsonl(low_confidence_path, (line for line in content_lines if line["confidence"] < 0.70))

    ids = [int(entry["id"]) for entry in entries]
    id_counts = collections.Counter(ids)
    duplicates = sorted(key for key, count in id_counts.items() if count > 1)
    max_id = max(ids, default=0)
    missing = sorted(set(range(1, VOLUME_01_MAX_ENTRY_ID + 1)) - set(ids))
    non_monotonic = []
    for previous, current in zip(ids, ids[1:]):
        if current <= previous:
            non_monotonic.append([previous, current])

    field_counts = collections.Counter()
    for entry in entries:
        field_counts.update(entry["fields"].keys())
    line_scores = [line["confidence"] for line in content_lines]
    quality = {
        "volume": 1,
        "pdf_pages": args.last_page,
        "content_pdf_pages": [args.first_content_page, args.last_page],
        "content_book_pages": [1, args.last_page - 88],
        "raw_line_count": len(content_lines),
        "front_matter_raw_line_count": len(front_lines),
        "raw_line_confidence": {
            "mean": round(statistics.fmean(line_scores), 6) if line_scores else None,
            "minimum": round(min(line_scores), 6) if line_scores else None,
            "below_0_80": sum(score < 0.80 for score in line_scores),
            "below_0_70": sum(score < 0.70 for score in line_scores),
        },
        "parsed_toc_entries": len(toc),
        "parsed_entries": len(entries),
        "entry_id_range": [min(ids, default=None), max_id or None],
        "missing_entry_ids_count": len(missing),
        "missing_entry_ids": missing,
        "duplicate_entry_ids": duplicates,
        "non_monotonic_pairs": non_monotonic,
        "entries_needing_review": len(issues),
        "field_counts": dict(field_counts.most_common()),
        "field_label_normalization": dict(label_stats),
    }
    quality_path = args.output / "volume_01_quality.json"
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "source_pdf": str(args.pdf),
        "source_pdf_sha256": sha256_file(args.pdf),
        "source_pdf_size": args.pdf.stat().st_size,
        "ocr_engine": "RapidOCR 3.9.2 / PP-OCRv6 small / ONNX Runtime 1.29.0",
        "rendering": "pdftoppm 250 DPI grayscale JPEG quality=95",
        "layout": {
            "pdf_pages_1_10": "single-page front matter",
            "pdf_pages_11_88": "three-column contents/index",
            "pdf_pages_89_1313": "two-column dictionary entries",
        },
        "correction_policy": [
            "Preserve raw per-line OCR, coordinates and confidence.",
            "Normalize field brackets and known field-label OCR variants.",
            "Normalize only O/o->0 and I/l->1 inside five-character entry IDs.",
            "Join visual line wraps inside fields.",
            "Do not guess corrections to herb names, formula names, quantities, or classical quotations.",
            "Use parsed table of contents as a comparison signal, not an automatic semantic overwrite.",
            "Apply audited page-and-text keyed header repairs from volume_01_header_corrections.json.",
        ],
        "header_corrections": str(args.header_corrections),
        "name_corrections": str(args.name_corrections) if args.name_corrections else None,
        "text_corrections": str(args.text_corrections),
        "outputs": {
            "raw_pages": str(args.raw_pages),
            "raw_text": str(raw_text_path),
            "front_matter_text": str(front_text_path),
            "clean_text": str(clean_text_path),
            "entries_jsonl": str(entries_path),
            "toc_jsonl": str(toc_path),
            "needs_review_jsonl": str(review_path),
            "low_confidence_lines_jsonl": str(low_confidence_path),
            "quality_json": str(quality_path),
        },
    }
    manifest["output_sha256"] = {
        "raw_text": sha256_file(raw_text_path),
        "front_matter_text": sha256_file(front_text_path),
        "clean_text": sha256_file(clean_text_path),
        "entries_jsonl": sha256_file(entries_path),
        "toc_jsonl": sha256_file(toc_path),
        "needs_review_jsonl": sha256_file(review_path),
        "low_confidence_lines_jsonl": sha256_file(low_confidence_path),
    }
    manifest_path = args.output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(quality, ensure_ascii=False, indent=2))
    return 0 if entries else 1


if __name__ == "__main__":
    raise SystemExit(main())
