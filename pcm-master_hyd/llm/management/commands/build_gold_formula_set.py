from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from llm_utils.rag.gold import build_gold_formula_set
from llm_utils.rag.paths import (
    gold_formula_metadata_path,
    gold_formula_set_path,
    treatment_prototypes_path,
)
from llm_utils.rag.paths import REPOSITORY_ROOT


class Command(BaseCommand):
    help = "从当前方剂索引构建 300—500 首可追溯核心方清单"

    def add_arguments(self, parser):
        parser.add_argument("--size", type=int, default=300)

    def handle(self, *args, **options):
        try:
            metadata = build_gold_formula_set(
                index_path=settings.RAG_INDEX_PATH,
                prototype_path=treatment_prototypes_path(),
                official_candidates_path=(
                    REPOSITORY_ROOT
                    / "pcm-master_hyd"
                    / "llm_utils"
                    / "rag"
                    / "official_core_candidates.json"
                ),
                output_path=gold_formula_set_path(),
                metadata_path=gold_formula_metadata_path(),
                target_size=options["size"],
            )
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                "核心方清单完成："
                f"{metadata['formula_count']} 首，"
                f"覆盖 {metadata['represented_prototype_count']}/"
                f"{metadata['prototype_count']} 个治疗原型"
            )
        )
