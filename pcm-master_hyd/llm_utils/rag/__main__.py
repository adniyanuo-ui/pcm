import argparse
import json
from pathlib import Path

from .index import FormulaIndexBuilder
from .paths import corpus_path, search_index_path, syndrome_index_path
from .retriever import FormulaRetriever, RetrievalQuery


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="《中医方剂大辞典》本地检索工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="构建一次性 SQLite 检索索引")
    build.add_argument("--corpus", type=Path, default=corpus_path())
    build.add_argument("--syndrome-index", type=Path, default=syndrome_index_path())
    build.add_argument("--output", type=Path, default=search_index_path())
    build.add_argument("--force", action="store_true", help="允许原子替换已有索引")

    status = subparsers.add_parser("status", help="查看当前索引元数据")
    status.add_argument("--index", type=Path, default=search_index_path())

    search = subparsers.add_parser("search", help="在本地索引中检索候选方")
    search.add_argument("--index", type=Path, default=search_index_path())
    search.add_argument("--free-text", default="")
    search.add_argument("--symptom", action="append", default=[])
    search.add_argument("--tongue", action="append", default=[])
    search.add_argument("--pulse", action="append", default=[])
    search.add_argument("--mechanism", action="append", default=[])
    search.add_argument("--syndrome", action="append", default=[])
    search.add_argument("--treatment", action="append", default=[])
    search.add_argument("--formula-name", action="append", default=[])
    search.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "build":
        if args.output.exists() and not args.force:
            raise SystemExit(f"索引已存在：{args.output}；如需重建请增加 --force")
        result = FormulaIndexBuilder(args.corpus, args.syndrome_index, args.output).build()
    elif args.command == "status":
        result = FormulaRetriever(args.index).metadata()
    else:
        query = RetrievalQuery.from_mapping(
            {
                "free_text": args.free_text,
                "symptoms": args.symptom,
                "tongue": args.tongue,
                "pulse": args.pulse,
                "mechanisms": args.mechanism,
                "syndromes": args.syndrome,
                "treatments": args.treatment,
                "formula_names": args.formula_name,
                "top_k": args.top_k,
            }
        )
        result = FormulaRetriever(args.index).search(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
