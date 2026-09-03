#!/usr/bin/env python3
"""OCR rendered pages of Zhong Yi Fang Ji Da Ci Dian with resumable output.

The script deliberately stores line coordinates and confidence scores before any
text cleanup.  That raw evidence is the durable result of the expensive OCR
step; later parsing/correction can be repeated without running OCR again.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import cv2
from rapidocr import RapidOCR


OCR_ENGINE: RapidOCR | None = None


def init_worker(threads: int, text_score: float) -> None:
    global OCR_ENGINE
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(threads))
    OCR_ENGINE = RapidOCR(
        params={
            "Global.text_score": text_score,
            "Global.log_level": "error",
            "EngineConfig.onnxruntime.intra_op_num_threads": threads,
            "EngineConfig.onnxruntime.inter_op_num_threads": 1,
        }
    )


def page_regions(pdf_page: int, width: int, height: int) -> list[tuple[str, int, int, int, int]]:
    """Return reading-order crop regions for this edition's fixed layouts."""
    if pdf_page <= 10:
        return [("page", int(width * 0.05), int(height * 0.04), int(width * 0.95), int(height * 0.95))]

    if pdf_page <= 88:
        # Contents and stroke index are three-column pages.
        # The scan alternates inner/outer margins on odd/even pages, so the
        # column boundaries need a small parity adjustment.  Do not overlap
        # these crops: a neighboring column's five-digit entry ID is otherwise
        # detected twice or with its prefix clipped.
        if pdf_page % 2:
            x_ranges = ((0.075, 0.36), (0.36, 0.62), (0.62, 0.94))
        else:
            x_ranges = ((0.065, 0.34), (0.34, 0.60), (0.60, 0.94))
        return [
            (f"column_{index}", int(width * x0), int(height * 0.055), int(width * x1), int(height * 0.93))
            for index, (x0, x1) in enumerate(x_ranges, 1)
        ]

    # Main dictionary text is two-column.  The small overlap only covers the
    # center rule and prevents characters adjacent to the rule being clipped.
    return [
        ("left", int(width * 0.06), int(height * 0.07), int(width * 0.49), int(height * 0.93)),
        ("right", int(width * 0.485), int(height * 0.07), int(width * 0.93), int(height * 0.93)),
    ]


def find_page_number(path: Path) -> int:
    match = re.search(r"(\d+)$", path.stem)
    if not match:
        raise ValueError(f"Cannot determine page number from {path.name}")
    return int(match.group(1))


def ocr_page(job: tuple[int, str, str]) -> dict[str, Any]:
    pdf_page, image_name, output_name = job
    output_path = Path(output_name)
    if output_path.exists() and output_path.stat().st_size > 100:
        return {"pdf_page": pdf_page, "status": "skipped"}

    started = time.time()
    img = cv2.imread(image_name)
    if img is None:
        raise RuntimeError(f"Cannot read rendered page: {image_name}")
    height, width = img.shape[:2]
    regions: list[dict[str, Any]] = []

    assert OCR_ENGINE is not None
    for region_name, x0, y0, x1, y1 in page_regions(pdf_page, width, height):
        crop = img[y0:y1, x0:x1]
        result = OCR_ENGINE(crop)
        lines: list[dict[str, Any]] = []
        boxes = result.boxes if result.boxes is not None else []
        texts = result.txts if result.txts is not None else []
        scores = result.scores if result.scores is not None else []
        for box, text, score in zip(boxes, texts, scores):
            adjusted = [[round(float(x) + x0, 2), round(float(y) + y0, 2)] for x, y in box]
            lines.append(
                {
                    "text": text.strip(),
                    "confidence": round(float(score), 6),
                    "box": adjusted,
                }
            )
        regions.append(
            {
                "name": region_name,
                "crop": [x0, y0, x1, y1],
                "lines": lines,
            }
        )

    payload = {
        "pdf_page": pdf_page,
        "book_page": pdf_page - 88 if pdf_page >= 89 else None,
        "image": {"width": width, "height": height, "file": Path(image_name).name},
        "layout": "two_column" if pdf_page >= 89 else ("three_column" if pdf_page >= 11 else "single_page"),
        "ocr": {"engine": "RapidOCR", "model": "PP-OCRv6", "version": "3.9.2"},
        "regions": regions,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(output_path)
    return {
        "pdf_page": pdf_page,
        "status": "done",
        "lines": sum(len(region["lines"]) for region in regions),
        "seconds": payload["elapsed_seconds"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--images", required=True, type=Path, help="Directory containing pdftoppm page images")
    parser.add_argument("--output", required=True, type=Path, help="Directory for one JSON file per PDF page")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--threads-per-worker", type=int, default=2)
    parser.add_argument("--text-score", type=float, default=0.30)
    args = parser.parse_args()

    image_by_page: dict[int, Path] = {}
    for path in sorted(args.images.glob("page-*.jpg")):
        image_by_page[find_page_number(path)] = path
    for path in sorted(args.images.glob("page-*.png")):
        image_by_page.setdefault(find_page_number(path), path)

    missing_images = [page for page in range(args.start, args.end + 1) if page not in image_by_page]
    if missing_images:
        print(f"Missing rendered images, first pages: {missing_images[:10]}", file=sys.stderr)
        return 2

    args.output.mkdir(parents=True, exist_ok=True)
    jobs = [
        (page, str(image_by_page[page]), str(args.output / f"page_{page:04d}.json"))
        for page in range(args.start, args.end + 1)
    ]

    started = time.time()
    done = skipped = lines = 0
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=args.workers,
        initializer=init_worker,
        initargs=(args.threads_per_worker, args.text_score),
    ) as executor:
        future_to_page = {executor.submit(ocr_page, job): job[0] for job in jobs}
        for future in concurrent.futures.as_completed(future_to_page):
            page = future_to_page[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"ERROR page {page}: {exc}", file=sys.stderr, flush=True)
                continue
            if result["status"] == "skipped":
                skipped += 1
            else:
                done += 1
                lines += result.get("lines", 0)
            completed = done + skipped
            if completed % 25 == 0 or completed == len(jobs):
                elapsed = time.time() - started
                rate = completed / elapsed if elapsed else 0
                print(
                    f"progress={completed}/{len(jobs)} done={done} skipped={skipped} "
                    f"lines={lines} rate={rate:.2f}_pages/s",
                    flush=True,
                )

    expected = args.end - args.start + 1
    actual = sum(1 for page in range(args.start, args.end + 1) if (args.output / f"page_{page:04d}.json").exists())
    if actual != expected:
        print(f"OCR incomplete: expected {expected} page files, found {actual}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
