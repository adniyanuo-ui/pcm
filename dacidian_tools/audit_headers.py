#!/usr/bin/env python3
"""Re-read disputed formula headers with a larger independent OCR recognizer.

A name correction is proposed only when the medium PP-OCRv6 reading of the
body header agrees with the separately scanned table-of-contents name.  The
script never changes dictionary content itself; it emits an auditable map for
clean_volume.py.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import cv2
from rapidocr import RapidOCR
from rapidocr.utils.typings import ModelType


HEADER_RE = re.compile(r"^\s*([0-9OoIlQ]{3,7})\s*(\D.*?)\s*[.…]*\s*$")

# These rare or stylized names cannot be decided reliably by OCR voting alone.
# Each decision was checked against the scan and the cited source/formula text.
VERIFIED_NAME_DECISIONS = {
    "00002": ("一匕金", "Verified against the cited 痘疹仁端录 formula; the stylized 匕 is repeatedly read as 七."),
    "00191": ("一捻金", "The entry itself gives the alias 小儿一捻金, confirming the body-header reading."),
    "00827": ("二姜丸", "The formula contains exactly 良姜 and 干姜; TOC and source meaning confirm 二姜丸."),
    "04484": ("三肉臛", "Verified against 寿亲养老/永乐大典 text and the three-meat soup preparation."),
    "04755": ("三瓶糁", "Verified against 徐评外科正宗 transcription and matching ingredients."),
    "05652": ("土萆薢汤", "Verified from the 土茯苓 alias and formula source; OCR cannot reliably read 萆薢."),
    "06919": ("大萆薢丸", "Verified from the composition and source; OCR cannot reliably read 萆薢."),
    "06920": ("大萆薢散", "Cross-reference counterpart of 萆薢散."),
    "08193": ("千缗汤", "Established formula name and body scan support 千缗汤."),
    "08644": ("己椒苈黄丸", "Established 金匮要略 abbreviation of 防己椒目葶苈大黄丸."),
    "08704": ("女萎膏", "Verified against 古今录验/证类本草 references."),
    "09308": ("小荜澄茄煎", "Verified against the 鸡峰普济方 source text and matching ingredients."),
}


def compact(text: str) -> str:
    return re.sub(r"[\s.…·]+", "", text)


def page_image(images_dir: Path, page: int) -> Path:
    matches = list(images_dir.glob(f"page-*{page}.jpg"))
    for path in matches:
        match = re.search(r"(\d+)$", path.stem)
        if match and int(match.group(1)) == page:
            return path
    raise FileNotFoundError(f"Rendered image for PDF page {page} not found")


def find_raw_line(page_data: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any] | None:
    targets = [entry.get("raw_header", "")]
    if entry.get("header_correction"):
        targets.insert(0, entry["header_correction"]["raw_text"])
    for region in page_data["regions"]:
        for line in region["lines"]:
            if line["text"] in targets:
                return line
    return None


def recognize_header(engine: RapidOCR, image: Any, box: list[list[float]]) -> tuple[str, float]:
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    x0 = max(0, int(min(xs)) - 14)
    x1 = min(image.shape[1], int(max(xs)) + 14)
    y0 = max(0, int(min(ys)) - 10)
    y1 = min(image.shape[0], int(max(ys)) + 10)
    result = engine(image[y0:y1, x0:x1], use_det=False, use_cls=False)
    if not result.txts:
        return "", 0.0
    return result.txts[0].strip(), float(result.scores[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entries", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--raw-pages", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--audit-output", required=True, type=Path)
    parser.add_argument("--corrections-output", required=True, type=Path)
    args = parser.parse_args()

    entries = {row["id"]: row for row in map(json.loads, args.entries.read_text(encoding="utf-8").splitlines())}
    disputed = [
        entry
        for entry in entries.values()
        if entry.get("toc")
        and (
            "name_differs_from_toc" in entry.get("quality_flags", [])
            or entry.get("name_correction")
        )
    ]
    engine = RapidOCR(
        params={
            "Global.log_level": "error",
            "EngineConfig.onnxruntime.intra_op_num_threads": 4,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
            "Rec.model_type": ModelType.MEDIUM,
        }
    )

    page_cache: dict[int, Any] = {}
    raw_cache: dict[int, dict[str, Any]] = {}
    audit_rows: list[dict[str, Any]] = []
    corrections: list[dict[str, Any]] = []
    for entry in disputed:
        page = entry["source"]["pdf_pages"][0]
        if page not in page_cache:
            page_cache[page] = cv2.imread(str(page_image(args.images, page)))
            raw_cache[page] = json.loads((args.raw_pages / f"page_{page:04d}.json").read_text(encoding="utf-8"))
        raw_line = find_raw_line(raw_cache[page], entry)
        if raw_line is None:
            audit_rows.append({"id": entry["id"], "status": "raw_header_box_not_found"})
            continue
        medium_text, medium_score = recognize_header(engine, page_cache[page], raw_line["box"])
        match = HEADER_RE.match(medium_text)
        medium_name = match.group(2).strip(" .…·") if match else ""
        body_name = entry.get("name_correction", {}).get("from", entry["name"])
        toc_name = entry["toc"]["name"]
        body_key = compact(body_name)
        toc_key = compact(toc_name)
        medium_key = compact(medium_name)
        verified = VERIFIED_NAME_DECISIONS.get(entry["id"])
        if verified:
            verified_name, reason = verified
            if compact(verified_name) != body_key:
                status = "correct_to_manually_verified_source_name"
                corrections.append(
                    {
                        "id": entry["id"],
                        "from_name": body_name,
                        "to_name": verified_name,
                        "method": reason,
                        "medium_ocr": medium_text,
                        "toc_ocr": toc_name,
                        "medium_confidence": round(medium_score, 6),
                        "pdf_page": page,
                    }
                )
            else:
                status = "keep_manually_verified_body_name"
        elif medium_key == toc_key and medium_key != body_key:
            status = "correct_to_medium_toc_consensus"
            corrections.append(
                {
                    "id": entry["id"],
                    "from_name": body_name,
                    "to_name": medium_name,
                    "method": "PP-OCRv6-medium body header agrees with independent TOC OCR",
                    "medium_ocr": medium_text,
                    "toc_ocr": toc_name,
                    "medium_confidence": round(medium_score, 6),
                    "pdf_page": page,
                }
            )
        elif medium_key == body_key:
            status = "keep_body_medium_consensus"
        else:
            status = "unresolved_three_way_disagreement"
        audit_rows.append(
            {
                "id": entry["id"],
                "pdf_page": page,
                "body_name": body_name,
                "toc_name": toc_name,
                "medium_ocr": medium_text,
                "medium_name": medium_name,
                "medium_confidence": round(medium_score, 6),
                "status": status,
            }
        )

    with args.audit_output.open("w", encoding="utf-8") as handle:
        for row in audit_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.corrections_output.write_text(json.dumps(corrections, ensure_ascii=False, indent=2), encoding="utf-8")
    summary: dict[str, int] = {}
    for row in audit_rows:
        summary[row["status"]] = summary.get(row["status"], 0) + 1
    print(json.dumps({"disputed": len(disputed), "corrections": len(corrections), "statuses": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
