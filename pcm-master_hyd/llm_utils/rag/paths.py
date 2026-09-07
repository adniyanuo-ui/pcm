import os
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def corpus_path() -> Path:
    return Path(
        os.getenv(
            "PCM_RAG_CORPUS_PATH",
            REPOSITORY_ROOT / "dacidian_text" / "corpus" / "fangji_entries.jsonl",
        )
    ).expanduser()


def syndrome_index_path() -> Path:
    return Path(
        os.getenv(
            "PCM_RAG_SYNDROME_INDEX_PATH",
            REPOSITORY_ROOT
            / "dacidian_text"
            / "volume_11"
            / "volume_11_syndrome_index.jsonl",
        )
    ).expanduser()


def search_index_path() -> Path:
    return Path(
        os.getenv(
            "PCM_RAG_INDEX_PATH",
            REPOSITORY_ROOT / "pcm-master_hyd" / "var" / "rag" / "fangji.sqlite3",
        )
    ).expanduser()


def treatment_prototypes_path() -> Path:
    return Path(
        os.getenv(
            "PCM_TREATMENT_PROTOTYPES_PATH",
            Path(__file__).resolve().with_name("treatment_prototypes.json"),
        )
    ).expanduser()


def gold_formula_set_path() -> Path:
    return Path(
        os.getenv(
            "PCM_GOLD_FORMULA_SET_PATH",
            Path(__file__).resolve().with_name("gold_formulas.jsonl"),
        )
    ).expanduser()


def gold_formula_metadata_path() -> Path:
    return Path(
        os.getenv(
            "PCM_GOLD_FORMULA_METADATA_PATH",
            Path(__file__).resolve().with_name("gold_formulas.meta.json"),
        )
    ).expanduser()
