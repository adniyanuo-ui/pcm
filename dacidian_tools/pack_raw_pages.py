#!/usr/bin/env python3
"""Pack/unpack resumable per-page OCR JSON as deterministic gzip JSONL."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def pack(input_dir: Path, output: Path) -> tuple[int, str]:
    files = sorted(input_dir.glob("page_*.json"))
    if not files:
        raise RuntimeError(f"No page_*.json files found in {input_dir}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    with temp.open("wb") as raw_handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, compresslevel=9, mtime=0) as gz:
            for path in files:
                payload = json.loads(path.read_text(encoding="utf-8"))
                line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
                gz.write(line.encode("utf-8"))
    temp.replace(output)
    return verify(output)


def unpack(input_path: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with gzip.open(input_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            page = int(payload["pdf_page"])
            path = output_dir / f"page_{page:04d}.json"
            temp = path.with_suffix(".json.tmp")
            temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(path)
            count += 1
    return count


def verify(path: Path) -> tuple[int, str]:
    pages: list[int] = []
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            pages.append(int(payload["pdf_page"]))
    if not pages:
        raise RuntimeError(f"Archive is empty: {path}")
    expected = list(range(min(pages), max(pages) + 1))
    if pages != expected:
        raise RuntimeError("Packed pages are missing, duplicated, or out of order")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return len(pages), digest


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pack_parser = sub.add_parser("pack")
    pack_parser.add_argument("--input", required=True, type=Path)
    pack_parser.add_argument("--output", required=True, type=Path)

    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--input", required=True, type=Path)

    unpack_parser = sub.add_parser("unpack")
    unpack_parser.add_argument("--input", required=True, type=Path)
    unpack_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    if args.command == "pack":
        count, digest = pack(args.input, args.output)
        print(json.dumps({"pages": count, "sha256": digest, "output": str(args.output)}, ensure_ascii=False))
    elif args.command == "verify":
        count, digest = verify(args.input)
        print(json.dumps({"pages": count, "sha256": digest, "input": str(args.input)}, ensure_ascii=False))
    else:
        count = unpack(args.input, args.output)
        print(json.dumps({"pages": count, "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

