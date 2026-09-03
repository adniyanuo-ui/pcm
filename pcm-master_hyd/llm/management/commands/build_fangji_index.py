import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from llm_utils.rag import FormulaIndexBuilder


class Command(BaseCommand):
    help = "从《中医方剂大辞典》结构化语料构建本地方剂检索索引"

    def add_arguments(self, parser):
        parser.add_argument("--corpus", type=Path, default=settings.RAG_CORPUS_PATH)
        parser.add_argument(
            "--syndrome-index", type=Path, default=settings.RAG_SYNDROME_INDEX_PATH
        )
        parser.add_argument("--output", type=Path, default=settings.RAG_INDEX_PATH)
        parser.add_argument(
            "--force", action="store_true", help="允许原子替换已经存在的索引"
        )

    def handle(self, *args, **options):
        output = options["output"]
        if output.exists() and not options["force"]:
            raise CommandError(f"索引已存在：{output}；如需重建请增加 --force")
        self.stdout.write(f"读取正编语料：{options['corpus']}")
        self.stdout.write(f"读取病证索引：{options['syndrome_index']}")
        metadata = FormulaIndexBuilder(
            options["corpus"], options["syndrome_index"], output
        ).build()
        self.stdout.write(self.style.SUCCESS(f"索引构建完成：{output}"))
        self.stdout.write(json.dumps(metadata, ensure_ascii=False, indent=2))
