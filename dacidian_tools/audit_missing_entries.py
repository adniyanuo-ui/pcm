#!/usr/bin/env python3
"""Print source context for missing dictionary entry identifiers.

This is a read-only diagnostic helper.  It correlates parser gaps with the
table of contents, neighbouring parsed entries, and nearby raw OCR lines so a
human can distinguish an OCR-damaged header from a genuinely missing scan.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--volume-dir", required=True, type=Path)
    parser.add_argument("--context", type=int, default=5)
    parser.add_argument(
        "--ids",
        help="Optional comma-separated subset of missing identifiers",
    )
    args = parser.parse_args()

    volume_dir = args.volume_dir
    prefix = volume_dir.name
    quality = json.loads((volume_dir / f"{prefix}_quality.json").read_text(encoding="utf-8"))
    entries = load_jsonl(volume_dir / f"{prefix}_entries.jsonl")
    toc = {row["id"]: row for row in load_jsonl(volume_dir / f"{prefix}_toc_index.jsonl")}
    by_id: dict[int, list[dict]] = {}
    for entry in entries:
        by_id.setdefault(int(entry["id"]), []).append(entry)

    parsed_ids = sorted(by_id)
    raw_pages = volume_dir / "raw_pages"
    requested = {int(value) for value in args.ids.split(",")} if args.ids else None
    for missing in quality["missing_entry_ids"]:
        if requested is not None and missing not in requested:
            continue
        before_id = max((item for item in parsed_ids if item < missing), default=None)
        after_id = min((item for item in parsed_ids if item > missing), default=None)
        before = by_id[before_id][-1] if before_id is not None else None
        after = by_id[after_id][0] if after_id is not None else None
        pages = set()
        for entry in (before, after):
            if entry:
                pages.update(entry["source"]["pdf_pages"][-1:])
                pages.update(entry["source"]["pdf_pages"][:1])
        print("=" * 88)
        print(
            json.dumps(
                {
                    "missing": f"{missing:05d}",
                    "toc": toc.get(f"{missing:05d}"),
                    "before": {
                        "id": before["id"],
                        "name": before["name"],
                        "pages": before["source"]["pdf_pages"],
                    }
                    if before
                    else None,
                    "after": {
                        "id": after["id"],
                        "name": after["name"],
                        "pages": after["source"]["pdf_pages"],
                    }
                    if after
                    else None,
                },
                ensure_ascii=False,
            )
        )
        for page in sorted(pages):
            path = raw_pages / f"page_{page:04d}.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"-- PDF page {page} --")
            for region in data["regions"]:
                lines = region["lines"]
                print(f"[{region['name']}] {len(lines)} lines")
                for index, line in enumerate(lines):
                    text = line["text"].strip()
                    if (
                        (before and (before["id"] in text or before["name"] in text))
                        or (after and (after["id"] in text or after["name"] in text))
                        or (toc.get(f"{missing:05d}") and toc[f"{missing:05d}"]["name"] in text)
                    ):
                        start = max(0, index - args.context)
                        end = min(len(lines), index + args.context + 1)
                        for line_index in range(start, end):
                            marker = ">" if line_index == index else " "
                            print(f"{marker} {line_index:03d} {lines[line_index]['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
