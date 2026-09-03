#!/usr/bin/env python3
"""Structure volume 11 formula, syndrome, measures, and bibliography indexes."""

from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import json
import re
import statistics
from pathlib import Path
from typing import Iterable

from clean_volume import cluster_visual_rows, compact_name, normalize_id, normalize_space


INDEX_ID_RE = re.compile(r"(?<![0-9OoIl])([0-9OoIl]{5})(?![0-9OoIl])")
CJK_RE = re.compile(r"[\u3400-\u9fff]")
MAJOR_CATEGORY_RE = re.compile(r"^[一二三四五六七八九十]+、")
MINOR_CATEGORY_RE = re.compile(r"^[（(][一二三四五六七八九十]+[）)]")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_pages(raw_pages: Path) -> list[dict]:
    pages = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(raw_pages.glob("page_*.json"))]
    if [page["pdf_page"] for page in pages] != list(range(1, 951)):
        raise RuntimeError("Volume 11 raw pages must contain the continuous PDF page range 1-950")
    return pages


def page_lines(pages: Iterable[dict], start: int, end: int) -> list[dict]:
    result: list[dict] = []
    for page in pages:
        if not start <= page["pdf_page"] <= end:
            continue
        for region in page["regions"]:
            for line_index, line in enumerate(region["lines"]):
                text = normalize_space(line["text"])
                if not text:
                    continue
                result.append(
                    {
                        "text": text,
                        "confidence": float(line["confidence"]),
                        "pdf_page": page["pdf_page"],
                        "book_page": page.get("book_page"),
                        "region": region["name"],
                        "line_index": line_index,
                        "box": line["box"],
                    }
                )
    return result


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_text_pages(path: Path, lines: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        last_page = None
        last_region = None
        for line in lines:
            if line["pdf_page"] != last_page:
                handle.write(
                    f"\n===== PDF_PAGE {line['pdf_page']:04d} / BOOK_PAGE {line.get('book_page')} =====\n"
                )
                last_page = line["pdf_page"]
                last_region = None
            if line["region"] != last_region:
                handle.write(f"--- {line['region']} ---\n")
                last_region = line["region"]
            handle.write(line["text"] + "\n")


def load_canonical_entries(path: Path) -> dict[str, dict]:
    return {
        row["id"]: row
        for row in (
            json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line
        )
    }


def edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for left_index, left_character in enumerate(left, 1):
        current = [left_index]
        for right_index, right_character in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_character != right_character),
                )
            )
        previous = current
    return previous[-1]


def numeric_candidates(raw: str, canonical: dict[str, dict]) -> tuple[str, set[str]]:
    translated = raw.translate(str.maketrans({"O": "0", "o": "0", "Q": "0", "I": "1", "l": "1", "B": "8", "S": "5"}))
    digits = re.sub(r"\D", "", translated)
    candidates: set[str] = set()
    if len(digits) <= 5:
        candidates.add(digits.zfill(5))
    if len(digits) == 4:
        for position in range(5):
            for digit in "0123456789":
                candidates.add(digits[:position] + digit + digits[position:])
    elif len(digits) == 5:
        for position in range(5):
            for digit in "0123456789":
                candidates.add(digits[:position] + digit + digits[position + 1 :])
    elif len(digits) == 6:
        for position in range(6):
            candidates.add(digits[:position] + digits[position + 1 :])
    return digits, {candidate for candidate in candidates if candidate in canonical}


def parse_formula_index(lines: list[dict], canonical: dict[str, dict]) -> tuple[list[dict], list[dict], dict]:
    parsed_by_id: dict[str, list[dict]] = collections.defaultdict(list)
    unparsed_candidates: list[dict] = []
    canonical_by_name: dict[str, list[str]] = collections.defaultdict(list)
    for entry_id, entry in canonical.items():
        canonical_by_name[compact_name(entry["name"])].append(entry_id)
    for row in cluster_visual_rows(lines, tolerance=14.0):
        text = normalize_space(row["text"])
        if "方名索引" in text or "总" in text:
            continue
        name_start = CJK_RE.search(text)
        if name_start is None:
            continue
        raw_id = text[: name_start.start()].strip()
        name = text[name_start.start() :].strip(" .·…—-")
        section = "正词目" if row["pdf_page"] <= 653 else "副词目"
        if not re.search(r"\d", raw_id) or not 3 <= len(re.sub(r"\D", "", raw_id)) <= 7:
            if re.search(r"\d{4,6}", text) and CJK_RE.search(text):
                unparsed_candidates.append({"reason": "unparsed_formula_index_row", **row})
            continue
        digits, candidates = numeric_candidates(raw_id, canonical)
        compact_ocr_name = compact_name(name)
        for candidate in canonical_by_name.get(compact_ocr_name, []):
            distance = min(
                edit_distance(digits, candidate),
                edit_distance(digits.zfill(5), candidate) if len(digits) < 5 else 99,
            )
            if distance <= 3:
                candidates.add(candidate)
        scored: list[tuple[float, int, str]] = []
        for candidate in candidates:
            similarity = difflib.SequenceMatcher(
                None, compact_ocr_name, compact_name(canonical[candidate]["name"])
            ).ratio()
            distance = min(
                edit_distance(digits, candidate),
                edit_distance(digits.zfill(5), candidate) if len(digits) < 5 else 99,
            )
            scored.append((similarity, distance, candidate))
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
        preferred_id = None
        if len(digits) == 5 and digits in candidates:
            preferred_id = digits
        elif len(digits) < 5 and digits.zfill(5) in candidates:
            preferred_id = digits.zfill(5)
        minimum_similarity = 0.65
        if preferred_id is not None:
            preferred_similarity = difflib.SequenceMatcher(
                None, compact_ocr_name, compact_name(canonical[preferred_id]["name"])
            ).ratio()
            best_alternative_similarity = scored[0][0] if scored else 0.0
            if preferred_similarity >= 0.50 or best_alternative_similarity < 0.80:
                scored = [
                    item for item in scored if item[2] == preferred_id
                ] + [item for item in scored if item[2] != preferred_id]
                minimum_similarity = 0.0
        if not scored or scored[0][0] < minimum_similarity:
            unparsed_candidates.append({"reason": "invalid_formula_id_or_name", **row})
            continue
        best_similarity, best_distance, entry_id = scored[0]
        if (
            preferred_id is None
            and len(scored) > 1
            and scored[1][:2] == scored[0][:2]
            and scored[1][2] != entry_id
        ):
            unparsed_candidates.append(
                {
                    "reason": "ambiguous_formula_index_id_repair",
                    "raw_id": raw_id,
                    "name": name,
                    "candidate_ids": [item[2] for item in scored if item[:2] == scored[0][:2]],
                    **row,
                }
            )
            continue
        canonical_name = canonical[entry_id]["name"]
        parsed_by_id[entry_id].append(
            {
                "id": entry_id,
                "name": name,
                "raw_id": raw_id,
                "index_section": section,
                "source": {
                    "volume": 11,
                    "pdf_page": row["pdf_page"],
                    "book_page": row["pdf_page"] - 11,
                    "region": row["region"],
                },
                "ocr_confidence": round(row["confidence"], 6),
                "canonical_name": canonical_name,
                "canonical_name_similarity": round(best_similarity, 4),
                "id_correction": {
                    "raw": raw_id,
                    "method": "canonical name plus bounded numeric edit distance",
                    "numeric_edit_distance": best_distance,
                }
                if raw_id != entry_id
                else None,
            }
        )

    initial_missing = set(canonical) - set(parsed_by_id)
    duplicate_reassignments = 0
    for duplicate_id, duplicate_rows in list(parsed_by_id.items()):
        if len(duplicate_rows) <= 1:
            continue
        duplicate_rows.sort(
            key=lambda item: (item["canonical_name_similarity"], item["ocr_confidence"]), reverse=True
        )
        retained = [duplicate_rows[0]]
        for duplicate_row in duplicate_rows[1:]:
            digits, candidates = numeric_candidates(duplicate_row["raw_id"], canonical)
            for candidate_id in canonical_by_name.get(compact_name(duplicate_row["name"]), []):
                distance = min(
                    edit_distance(digits, candidate_id),
                    edit_distance(digits.zfill(5), candidate_id) if len(digits) < 5 else 99,
                )
                if distance <= 3:
                    candidates.add(candidate_id)
            candidates &= initial_missing
            scored = []
            for candidate_id in candidates:
                similarity = difflib.SequenceMatcher(
                    None,
                    compact_name(duplicate_row["name"]),
                    compact_name(canonical[candidate_id]["name"]),
                ).ratio()
                distance = min(
                    edit_distance(digits, candidate_id),
                    edit_distance(digits.zfill(5), candidate_id) if len(digits) < 5 else 99,
                )
                scored.append((similarity, distance, candidate_id))
            scored.sort(key=lambda item: (-item[0], item[1], item[2]))
            unambiguous = not (
                len(scored) > 1 and scored[0][:2] == scored[1][:2]
            )
            if scored and scored[0][0] >= 0.65 and unambiguous:
                similarity, distance, repaired_id = scored[0]
                repaired = dict(duplicate_row)
                repaired["id"] = repaired_id
                repaired["canonical_name"] = canonical[repaired_id]["name"]
                repaired["canonical_name_similarity"] = round(similarity, 4)
                repaired["id_correction"] = {
                    "raw": duplicate_row["raw_id"],
                    "method": "duplicate OCR ID reassigned to an otherwise missing canonical ID using name and numeric distance",
                    "numeric_edit_distance": distance,
                }
                parsed_by_id[repaired_id].append(repaired)
                initial_missing.remove(repaired_id)
                duplicate_reassignments += 1
            else:
                retained.append(duplicate_row)
        parsed_by_id[duplicate_id] = retained

    rows: list[dict] = []
    review = list(unparsed_candidates)
    for entry_id in sorted(parsed_by_id):
        candidates = parsed_by_id[entry_id]
        candidates.sort(
            key=lambda item: (item["canonical_name_similarity"], item["ocr_confidence"]), reverse=True
        )
        rows.append(candidates[0])
        if len(candidates) > 1:
            review.append(
                {
                    "reason": "duplicate_formula_id_in_index_ocr",
                    "id": entry_id,
                    "candidates": candidates,
                }
            )
        if candidates[0]["canonical_name_similarity"] < 0.70:
            review.append({"reason": "formula_name_differs_from_canonical", **candidates[0]})

    missing = sorted(set(canonical) - set(parsed_by_id))
    for entry_id in missing:
        review.append(
            {
                "reason": "formula_id_missing_from_parsed_volume_11_index",
                "id": entry_id,
                "canonical_name": canonical[entry_id]["name"],
            }
        )
    quality = {
        "parsed_rows": len(rows),
        "unique_ids": len(parsed_by_id),
        "missing_ids_count": len(missing),
        "missing_ids_sample": missing[:200],
        "duplicate_ids_count": sum(len(items) > 1 for items in parsed_by_id.values()),
        "duplicate_rows_reassigned": duplicate_reassignments,
        "low_name_similarity_count": sum(row["canonical_name_similarity"] < 0.70 for row in rows),
        "unparsed_candidate_rows": len(unparsed_candidates),
        "section_counts": dict(collections.Counter(row["index_section"] for row in rows)),
    }
    return rows, review, quality


def is_running_header(text: str) -> bool:
    return (
        "主治病证索引" in text
        or "总" in text
        or re.fullmatch(r"\d{1,4}", text) is not None
        or text in {"证索引", "主治病", "画"}
    )


def clean_term(text: str) -> str:
    text = re.sub(r"^[|:：·.\s]+|[|:：·.\s]+$", "", text)
    return text


def parse_syndrome_index(lines: list[dict], canonical: dict[str, dict]) -> tuple[list[dict], list[dict], dict]:
    rows = cluster_visual_rows(lines, tolerance=13.0)
    major_category = ""
    minor_category = ""
    current: dict | None = None
    occurrences: list[dict] = []
    review: list[dict] = []
    invalid_ids: collections.Counter = collections.Counter()

    def flush() -> None:
        nonlocal current
        if current and current["entry_ids"]:
            current["entry_ids"] = list(dict.fromkeys(current["entry_ids"]))
            occurrences.append(current)
        current = None

    for row in rows:
        text = normalize_space(row["text"])
        if not text or is_running_header(text):
            continue
        matches = list(INDEX_ID_RE.finditer(text))
        valid_ids: list[str] = []
        for match in matches:
            entry_id = normalize_id(match.group(1))
            if entry_id in canonical:
                valid_ids.append(entry_id)
            else:
                invalid_ids[entry_id] += 1
        first_id_start = matches[0].start() if matches else len(text)
        term_text = clean_term(text[:first_id_start])

        if MAJOR_CATEGORY_RE.match(term_text) or term_text.endswith("科病证"):
            flush()
            major_category = term_text
            minor_category = ""
            continue
        if MINOR_CATEGORY_RE.match(term_text):
            flush()
            minor_category = term_text
            continue
        if term_text and CJK_RE.search(term_text):
            flush()
            current = {
                "term": term_text,
                "category": {"major": major_category, "minor": minor_category},
                "entry_ids": [],
                "source": {"volume": 11, "pdf_pages": [], "book_pages": []},
                "raw_rows": [],
            }
        if valid_ids:
            if current is None:
                review.append({"reason": "orphan_formula_ids_without_syndrome_term", **row})
                continue
            current["entry_ids"].extend(valid_ids)
            current["source"]["pdf_pages"].append(row["pdf_page"])
            current["source"]["book_pages"].append(row["pdf_page"] - 11)
            current["raw_rows"].append(text)
        elif not term_text and re.search(r"\d", text):
            review.append({"reason": "unparsed_numeric_syndrome_row", **row})
    flush()

    combined: dict[tuple[str, str, str], dict] = {}
    for item in occurrences:
        key = (item["category"]["major"], item["category"]["minor"], item["term"])
        if key not in combined:
            combined[key] = item
            continue
        target = combined[key]
        target["entry_ids"].extend(item["entry_ids"])
        target["entry_ids"] = list(dict.fromkeys(target["entry_ids"]))
        target["source"]["pdf_pages"].extend(item["source"]["pdf_pages"])
        target["source"]["book_pages"].extend(item["source"]["book_pages"])
        target["raw_rows"].extend(item["raw_rows"])
    result = list(combined.values())
    for item in result:
        item["source"]["pdf_pages"] = sorted(set(item["source"]["pdf_pages"]))
        item["source"]["book_pages"] = sorted(set(item["source"]["book_pages"]))
        item["entry_count"] = len(item["entry_ids"])

    quality = {
        "syndrome_terms": len(result),
        "formula_relations": sum(item["entry_count"] for item in result),
        "unique_formula_ids_referenced": len({entry_id for item in result for entry_id in item["entry_ids"]}),
        "invalid_formula_ids": dict(invalid_ids.most_common()),
        "review_rows": len(review),
    }
    return result, review, quality


def table_rows(lines: list[dict], section: str) -> list[dict]:
    return [
        {"section": section, "book_page": row["pdf_page"] - 11, **row}
        for row in cluster_visual_rows(lines, tolerance=14.0)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-pages", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--canonical-entries", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    pages = load_pages(args.raw_pages)
    canonical = load_canonical_entries(args.canonical_entries)
    if len(canonical) != 96592:
        raise RuntimeError("Canonical corpus must contain exactly 96592 formula records")

    all_lines = page_lines(pages, 1, 950)
    front_lines = page_lines(pages, 1, 11)
    formula_lines = page_lines(pages, 12, 757)
    syndrome_lines = page_lines(pages, 758, 929)
    measures_lines = page_lines(pages, 930, 933)
    bibliography_lines = page_lines(pages, 934, 950)

    formula_rows, formula_review, formula_quality = parse_formula_index(formula_lines, canonical)
    formula_by_id = {row["id"]: row for row in formula_rows}
    complete_formula_rows = []
    for entry_id in sorted(canonical):
        ocr_row = formula_by_id.get(entry_id)
        complete_formula_rows.append(
            {
                "id": entry_id,
                "name": canonical[entry_id]["name"],
                "index_record_status": "ocr_matched" if ocr_row else "supplemented_from_canonical_corpus",
                "volume_11_ocr": ocr_row,
                "quality_flags": [] if ocr_row else ["not_located_in_volume_11_formula_index_ocr"],
            }
        )
    syndrome_rows, syndrome_review, syndrome_quality = parse_syndrome_index(syndrome_lines, canonical)
    measures_rows = table_rows(measures_lines, "古今度量衡对照")
    bibliography_rows = table_rows(bibliography_lines, "主要引用书目")

    raw_text_path = args.output / "volume_11_raw.txt"
    front_text_path = args.output / "volume_11_front_matter.txt"
    measures_text_path = args.output / "volume_11_measures.txt"
    bibliography_text_path = args.output / "volume_11_bibliography.txt"
    write_text_pages(raw_text_path, all_lines)
    write_text_pages(front_text_path, front_lines)
    write_text_pages(measures_text_path, measures_lines)
    write_text_pages(bibliography_text_path, bibliography_lines)

    formula_path = args.output / "volume_11_formula_index.jsonl"
    complete_formula_path = args.output / "volume_11_formula_index_complete.jsonl"
    formula_review_path = args.output / "volume_11_formula_index_needs_review.jsonl"
    syndrome_path = args.output / "volume_11_syndrome_index.jsonl"
    syndrome_review_path = args.output / "volume_11_syndrome_index_needs_review.jsonl"
    measures_rows_path = args.output / "volume_11_measure_rows.jsonl"
    bibliography_rows_path = args.output / "volume_11_bibliography_rows.jsonl"
    write_jsonl(formula_path, formula_rows)
    write_jsonl(complete_formula_path, complete_formula_rows)
    write_jsonl(formula_review_path, formula_review)
    write_jsonl(syndrome_path, syndrome_rows)
    write_jsonl(syndrome_review_path, syndrome_review)
    write_jsonl(measures_rows_path, measures_rows)
    write_jsonl(bibliography_rows_path, bibliography_rows)

    scores = [line["confidence"] for line in all_lines]
    blank_pages = [page["pdf_page"] for page in pages if not any(region["lines"] for region in page["regions"])]
    quality = {
        "volume": 11,
        "pdf_pages": 950,
        "book_pages": [1, 939],
        "raw_line_count": len(all_lines),
        "raw_line_confidence": {
            "mean": round(statistics.fmean(scores), 6),
            "minimum": round(min(scores), 6),
            "below_0_80": sum(score < 0.80 for score in scores),
            "below_0_70": sum(score < 0.70 for score in scores),
        },
        "blank_pdf_pages": blank_pages,
        "sections": {
            "front_matter": [1, 11],
            "formula_primary_index": [12, 653],
            "formula_secondary_index": [654, 757],
            "syndrome_index": [758, 929],
            "measures": [930, 933],
            "bibliography": [934, 950],
        },
        "formula_index": formula_quality,
        "syndrome_index": syndrome_quality,
        "measure_rows": len(measures_rows),
        "bibliography_rows": len(bibliography_rows),
    }
    quality["formula_index"]["complete_logical_rows"] = len(complete_formula_rows)
    quality["formula_index"]["supplemented_from_canonical_corpus"] = sum(
        row["index_record_status"] == "supplemented_from_canonical_corpus"
        for row in complete_formula_rows
    )
    quality_path = args.output / "volume_11_quality.json"
    quality_path.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")

    output_paths = [
        raw_text_path,
        front_text_path,
        measures_text_path,
        bibliography_text_path,
        formula_path,
        complete_formula_path,
        formula_review_path,
        syndrome_path,
        syndrome_review_path,
        measures_rows_path,
        bibliography_rows_path,
        quality_path,
    ]
    manifest = {
        "volume": 11,
        "source_pdf": str(args.pdf),
        "source_pdf_sha256": sha256_file(args.pdf),
        "source_pdf_size": args.pdf.stat().st_size,
        "ocr_engine": "RapidOCR 3.9.2 / PP-OCRv6 small / ONNX Runtime 1.29.0",
        "rendering": "pdftoppm 250 DPI grayscale JPEG quality=95",
        "layout": "pages 12-757 three-column; 758-929 two-column; 930-950 full-page",
        "canonical_formula_corpus": str(args.canonical_entries),
        "outputs": {path.name: sha256_file(path) for path in output_paths},
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(quality, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
