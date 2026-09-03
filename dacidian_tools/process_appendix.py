#!/usr/bin/env python3
"""Render, OCR, structure, and archive dictionary appendix volume 11."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    print("RUN", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--threads-per-worker", type=int, default=2)
    parser.add_argument("--keep-rendered-pages", action="store_true")
    args = parser.parse_args()

    pdf = ROOT / "dacidian_pdf" / "中医方剂大辞典（第11册）.pdf"
    output = ROOT / "dacidian_text" / "volume_11"
    raw_pages = output / "raw_pages"
    images = Path("/tmp/dacidian_v11_pages")
    canonical = ROOT / "dacidian_text" / "corpus" / "fangji_entries.jsonl"
    if not canonical.exists():
        raise RuntimeError("Run merge_corpus.py after completing volumes 1-10 first")
    output.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    if len(list(images.glob("page-*.jpg"))) != 950:
        run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-l",
                "950",
                "-jpeg",
                "-jpegopt",
                "quality=95,optimize=y",
                "-r",
                "250",
                "-gray",
                str(pdf),
                str(images / "page"),
            ]
        )
    run(
        [
            sys.executable,
            str(TOOLS / "ocr_volume.py"),
            "--images",
            str(images),
            "--output",
            str(raw_pages),
            "--start",
            "1",
            "--end",
            "950",
            "--volume",
            "11",
            "--content-start",
            "758",
            "--front-end",
            "11",
            "--book-page-start",
            "12",
            "--layout-profile",
            "appendix",
            "--workers",
            str(args.workers),
            "--threads-per-worker",
            str(args.threads_per_worker),
        ]
    )
    run(
        [
            sys.executable,
            str(TOOLS / "pack_raw_pages.py"),
            "pack",
            "--input",
            str(raw_pages),
            "--output",
            str(output / "volume_11_raw_pages.jsonl.gz"),
        ]
    )
    run(
        [
            sys.executable,
            str(TOOLS / "clean_appendix.py"),
            "--raw-pages",
            str(raw_pages),
            "--output",
            str(output),
            "--pdf",
            str(pdf),
            "--canonical-entries",
            str(canonical),
        ]
    )
    if not args.keep_rendered_pages:
        shutil.rmtree(images)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
