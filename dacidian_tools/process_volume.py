#!/usr/bin/env python3
"""Render, OCR, structure, and archive one configured dictionary volume."""

from __future__ import annotations

import argparse
import json
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
    parser.add_argument("--volume", required=True, type=int)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--threads-per-worker", type=int, default=2)
    parser.add_argument("--dpi", type=int, default=250)
    parser.add_argument("--keep-rendered-pages", action="store_true")
    args = parser.parse_args()

    configs = json.loads((TOOLS / "volumes.json").read_text(encoding="utf-8"))
    config = next((item for item in configs if item["volume"] == args.volume), None)
    if config is None:
        raise RuntimeError(f"Volume {args.volume} is not configured")
    if config["kind"] != "dictionary":
        raise RuntimeError("Appendix volume 11 uses a separate OCR/index workflow")

    volume = args.volume
    prefix = f"volume_{volume:02d}"
    pdf = ROOT / "dacidian_pdf" / f"中医方剂大辞典（第{volume}册）.pdf"
    output = ROOT / "dacidian_text" / prefix
    raw_pages = output / "raw_pages"
    images = Path("/tmp") / f"dacidian_v{volume:02d}_pages"
    output.mkdir(parents=True, exist_ok=True)
    images.mkdir(parents=True, exist_ok=True)

    expected_images = config["pages"]
    existing_images = len(list(images.glob("page-*.jpg")))
    if existing_images != expected_images:
        run(
            [
                "pdftoppm",
                "-f",
                "1",
                "-l",
                str(config["pages"]),
                "-jpeg",
                "-jpegopt",
                "quality=95,optimize=y",
                "-r",
                str(args.dpi),
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
            str(config["pages"]),
            "--volume",
            str(volume),
            "--content-start",
            str(config["content_start"]),
            "--workers",
            str(args.workers),
            "--threads-per-worker",
            str(args.threads_per_worker),
        ]
    )

    name_corrections = output / f"{prefix}_name_corrections.json"
    clean_command = [
        sys.executable,
        str(TOOLS / "clean_volume.py"),
        "--volume",
        str(volume),
        "--raw-pages",
        str(raw_pages),
        "--output",
        str(output),
        "--pdf",
        str(pdf),
        "--first-content-page",
        str(config["content_start"]),
        "--last-page",
        str(config["pages"]),
        "--first-entry-id",
        str(config["first_entry_id"]),
        "--last-entry-id",
        str(config["last_entry_id"]),
    ]
    if name_corrections.exists():
        clean_command.extend(["--name-corrections", str(name_corrections)])
    run(clean_command)

    run(
        [
            sys.executable,
            str(TOOLS / "pack_raw_pages.py"),
            "pack",
            "--input",
            str(raw_pages),
            "--output",
            str(output / f"{prefix}_raw_pages.jsonl.gz"),
        ]
    )

    if not args.keep_rendered_pages:
        shutil.rmtree(images)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
