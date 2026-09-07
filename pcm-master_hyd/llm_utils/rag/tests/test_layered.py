import json
import tempfile
import unittest
from pathlib import Path

from llm_utils.rag import FormulaIndexBuilder, LayeredFormulaRetriever
from llm_utils.rag.paths import (
    gold_formula_metadata_path,
    gold_formula_set_path,
    treatment_prototypes_path,
)


class LayeredFormulaRetrieverTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        corpus = root / "entries.jsonl"
        syndrome = root / "syndromes.jsonl"
        self.index = root / "fangji.sqlite3"
        self.gold = root / "gold.jsonl"
        self.gold_metadata = root / "gold.meta.json"
        records = [
            {
                "id": "00001",
                "name": "四君子汤",
                "fields": {
                    "方源": "《鸡峰》卷十二。",
                    "组成": "人参 白术 茯苓 甘草",
                    "功用": "益气健脾。",
                    "主治": "脾胃气虚，食少便溏，体倦乏力。",
                },
                "source": {"volume": 3, "pdf_pages": [554], "book_pages": [449]},
                "quality_flags": [],
            },
            {
                "id": "00002",
                "name": "参苓白术散",
                "fields": {
                    "方源": "《局方》卷三。",
                    "组成": "人参 白术 茯苓 山药 莲子 白扁豆 薏苡仁 砂仁 桔梗 甘草",
                    "功用": "健脾益气，和胃渗湿。",
                    "主治": "脾胃虚弱，食少便溏，四肢乏力。",
                    "方论选录": "人参、白术健脾益气，茯苓、薏苡仁渗湿。",
                },
                "source": {"volume": 6, "pdf_pages": [220], "book_pages": [112]},
                "quality_flags": [],
            },
            {
                "id": "00003",
                "name": "理中丸",
                "fields": {
                    "方源": "《伤寒论》。",
                    "组成": "人参 干姜 白术 甘草",
                    "功用": "温中祛寒，补气健脾。",
                    "主治": "中焦虚寒，腹痛便溏，不欲饮食。",
                },
                "source": {"volume": 5, "pdf_pages": [300], "book_pages": [211]},
                "quality_flags": [],
            },
        ]
        corpus.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
        )
        syndrome.write_text("", encoding="utf-8")
        metadata = FormulaIndexBuilder(corpus, syndrome, self.index).build()

        # GoldFormulaSet 的生产门禁要求 300—500 行；不存在于测试索引的占位 ID
        # 只为轻量测试 ready/唯一性门禁，search_subset 只会读取真实存在的三条记录。
        core = [
            {
                "id": "00001",
                "name": "四君子汤",
                "primary_prototype_id": "tonify_spleen_qi",
                "prototype_ids": ["tonify_spleen_qi"],
                "review_status": "test_fixture",
            },
            {
                "id": "00002",
                "name": "参苓白术散",
                "primary_prototype_id": "tonify_spleen_drain_damp",
                "prototype_ids": ["tonify_spleen_drain_damp", "tonify_spleen_qi"],
                "review_status": "test_fixture",
            },
        ]
        core.extend(
            {
                "id": f"fixture-{index:03d}",
                "name": f"测试核心方{index:03d}",
                "primary_prototype_id": "tonify_spleen_qi",
                "prototype_ids": ["tonify_spleen_qi"],
                "review_status": "test_fixture",
            }
            for index in range(298)
        )
        self.gold.write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in core),
            encoding="utf-8",
        )
        self.gold_metadata.write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "formula_count": 300,
                    "prototype_count": 62,
                    "index_corpus_sha256": metadata["corpus_sha256"],
                }
            ),
            encoding="utf-8",
        )
        self.retriever = LayeredFormulaRetriever(
            self.index,
            treatment_prototypes_path(),
            self.gold,
            self.gold_metadata,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_composite_family_core_formula_stops_before_archive(self):
        result = self.retriever.search(
            {
                "symptoms": ["食少", "便溏", "乏力"],
                "mechanisms": ["脾气虚弱", "湿邪内停"],
                "treatments": ["健脾益气", "渗湿", "和胃"],
                "top_k": 2,
            },
            clinical_profile={
                "nature": ["虚", "湿"],
                "primary_pathogenesis": ["脾气虚弱"],
                "secondary_pathogenesis": ["湿邪内停"],
                "primary_treatment": ["健脾益气"],
                "secondary_treatment": ["渗湿"],
                "adjunct_treatment": ["和胃"],
            },
            full_fields=True,
        )
        self.assertEqual(result["retrieval"]["stopped_at"], "core")
        self.assertFalse(result["retrieval"]["fallback_used"])
        self.assertEqual(result["candidates"][0]["name"], "参苓白术散")
        self.assertEqual(
            result["candidates"][0]["treatment_family"]["name"], "健脾益气渗湿"
        )
        validation = result["candidates"][0]["reverse_validation"]
        self.assertEqual(validation["consistency"], "较高")
        self.assertFalse(validation["facts_inferred_by_model"])
        self.assertIn("人参、白术", validation["formula_meaning"])

    def test_missing_core_family_falls_back_to_archive(self):
        result = self.retriever.search(
            {
                "symptoms": ["腹痛", "便溏", "不欲饮食"],
                "mechanisms": ["中焦虚寒"],
                "treatments": ["温中祛寒"],
                "top_k": 2,
            },
            clinical_profile={
                "nature": ["寒", "虚"],
                "primary_pathogenesis": ["中焦虚寒"],
                "primary_treatment": ["温中祛寒"],
            },
            full_fields=True,
        )
        self.assertTrue(result["retrieval"]["fallback_used"])
        self.assertEqual(result["retrieval"]["stopped_at"], "archive")
        self.assertEqual(result["candidates"][0]["name"], "理中丸")
        self.assertEqual(result["candidates"][0]["selection_layer"], "archive")

    def test_reverse_validation_rejects_direction_conflict(self):
        result = self.retriever.search(
            {
                "symptoms": ["腹痛", "便溏"],
                "mechanisms": ["中焦湿热"],
                "treatments": ["温中祛寒"],
                "top_k": 2,
            },
            clinical_profile={
                "nature": ["热"],
                "primary_pathogenesis": ["中焦湿热"],
                "primary_treatment": ["温中祛寒"],
            },
            full_fields=True,
        )
        self.assertFalse(result["retrieval"]["fallback_used"])
        self.assertEqual(result["retrieval"]["stopped_at"], "clinical_profile")
        self.assertEqual(result["retrieval"]["validation_status"], "clinical_profile_conflict")
        self.assertIn("偏热", result["retrieval"]["profile_conflicts"][0])
        self.assertEqual(result["candidates"], [])


class PackagedFormulaKnowledgeTests(unittest.TestCase):
    def test_packaged_gold_set_is_unique_auditable_and_in_range(self):
        prototypes = json.loads(treatment_prototypes_path().read_text(encoding="utf-8"))
        records = [
            json.loads(line)
            for line in gold_formula_set_path().read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        metadata = json.loads(gold_formula_metadata_path().read_text(encoding="utf-8"))
        prototype_ids = {item["id"] for item in prototypes}
        self.assertTrue(40 <= len(prototypes) <= 100)
        self.assertTrue(300 <= len(records) <= 500)
        self.assertEqual(len({record["id"] for record in records}), len(records))
        self.assertEqual(len({record["name"] for record in records}), len(records))
        self.assertEqual(metadata["formula_count"], len(records))
        self.assertEqual(
            {prototype_id for record in records for prototype_id in record["prototype_ids"]},
            prototype_ids,
        )
        self.assertTrue(all(not record["clinical_reviewed"] for record in records))
        self.assertTrue(all(record["same_name_record_count"] >= 1 for record in records))


if __name__ == "__main__":
    unittest.main()
