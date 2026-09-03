import json
import tempfile
import unittest
from pathlib import Path

from llm_utils.rag import FormulaIndexBuilder, FormulaRetriever, RetrievalQuery


class FormulaRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.corpus = root / "entries.jsonl"
        self.syndromes = root / "syndromes.jsonl"
        self.index = root / "fangji.sqlite3"
        records = [
            {
                "id": "00001",
                "name": "四君子汤",
                "fields": {
                    "方源": "《鸡峰》卷十二。",
                    "组成": "人参 白术 茯苓 甘草",
                    "功用": "益气健脾。",
                    "主治": "脾胃气虚，食少便溏，体倦乏力，面色少华，脉细弱。",
                },
                "source": {"volume": 3, "pdf_pages": [554], "book_pages": [449]},
                "quality_flags": [],
            },
            {
                "id": "00002",
                "name": "六君子汤",
                "fields": {
                    "方源": "《医学正传》。",
                    "组成": "人参 白术 茯苓 甘草 陈皮 半夏",
                    "功用": "益气健脾，理气化痰。",
                    "主治": "脾胃虚弱，气逆痰滞，食少便溏。",
                },
                "source": {"volume": 2, "pdf_pages": [1144], "book_pages": [1060]},
                "quality_flags": [],
            },
            {
                "id": "00003",
                "name": "缺页方",
                "record_status": "source_page_missing",
                "fields": {"主治": "脾胃气虚，食少便溏。"},
                "source": {"volume": 5, "pdf_pages": [477], "book_pages": [390]},
                "quality_flags": ["excluded_from_rag_until_recovered"],
            },
            {
                "id": "00004",
                "name": "桂枝汤",
                "fields": {
                    "方源": "《伤寒论》。",
                    "功用": "解肌发表，调和营卫。",
                    "主治": "外感风寒表虚证。",
                },
                "source": {"volume": 6, "pdf_pages": [100], "book_pages": [20]},
                "quality_flags": [],
            },
        ]
        self.corpus.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
        syndrome_record = {
            "term": "脾胃虚弱",
            "category": {"major": "内科病证", "minor": "脾胃病证"},
            "entry_ids": ["00001", "00002", "00003"],
            "source": {"volume": 11, "pdf_pages": [800], "book_pages": [789]},
        }
        self.syndromes.write_text(
            json.dumps(syndrome_record, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self.metadata = FormulaIndexBuilder(self.corpus, self.syndromes, self.index).build()
        self.retriever = FormulaRetriever(self.index)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_builder_excludes_incomplete_source_records(self) -> None:
        self.assertEqual(self.metadata["total_records"], 4)
        self.assertEqual(self.metadata["indexed_records"], 3)
        self.assertEqual(self.metadata["excluded_records"], 1)
        result = self.retriever.search({"formula_names": ["缺页方"]})
        self.assertEqual(result["candidates"], [])

    def test_exact_formula_name_is_ranked_first(self) -> None:
        result = self.retriever.search({"formula_names": ["四君子汤"], "top_k": 3})
        self.assertEqual(result["candidates"][0]["id"], "00001")
        self.assertIn("方名精确匹配", result["candidates"][0]["match_reasons"])

    def test_clinical_fields_rank_matching_formula(self) -> None:
        query = RetrievalQuery.from_mapping(
            {
                "symptoms": ["乏力", "食少", "便溏"],
                "pulse": ["脉细弱"],
                "mechanisms": ["脾胃气虚"],
                "treatments": ["益气健脾"],
                "top_k": 3,
            }
        )
        result = self.retriever.search(query)
        first = result["candidates"][0]
        self.assertEqual(first["name"], "四君子汤")
        self.assertGreater(first["evidence_coverage"], 50)
        self.assertEqual(first["source"]["pdf_pages"], [554])

    def test_syndrome_index_is_a_recall_route_with_source(self) -> None:
        result = self.retriever.search({"syndromes": ["脾胃虚弱"], "top_k": 3})
        first = result["candidates"][0]
        self.assertTrue(first["syndrome_index_hits"])
        self.assertEqual(first["syndrome_index_hits"][0]["source"]["volume"], 11)

    def test_empty_or_invalid_query_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "至少提供"):
            RetrievalQuery.from_mapping({})
        with self.assertRaisesRegex(ValueError, "1—20"):
            RetrievalQuery.from_mapping({"symptoms": ["乏力"], "top_k": 21})


if __name__ == "__main__":
    unittest.main()
