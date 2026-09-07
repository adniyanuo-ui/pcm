import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from llm.cms.views import FormulaSearchView
from llm_utils.rag import FormulaIndexBuilder
from llm_utils.rag import FormulaRetriever


class FormulaSearchApiTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(cls.temporary_directory.name)
        corpus = root / "entries.jsonl"
        syndromes = root / "syndromes.jsonl"
        cls.index = root / "index.sqlite3"
        corpus.write_text(
            json.dumps(
                {
                    "id": "10001",
                    "name": "四君子汤",
                    "fields": {
                        "方源": "《鸡峰》。",
                        "组成": "人参 白术 茯苓 甘草",
                        "功用": "益气健脾。",
                        "主治": "脾胃气虚，食少便溏，体倦乏力。",
                    },
                    "source": {"volume": 3, "pdf_pages": [554], "book_pages": [449]},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        syndromes.write_text(
            json.dumps(
                {
                    "term": "脾胃气虚",
                    "category": {"major": "内科", "minor": "脾胃"},
                    "entry_ids": ["10001"],
                    "source": {"volume": 11, "pdf_pages": [800], "book_pages": [789]},
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        FormulaIndexBuilder(corpus, syndromes, cls.index).build()
        cls.factory = APIRequestFactory()
        cls.user = SimpleNamespace(id=1, is_authenticated=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()
        super().tearDownClass()

    def test_status_and_search(self):
        with self.settings(RAG_INDEX_PATH=self.index):
            request = self.factory.get("/api/cms/llm/rag/search/")
            force_authenticate(request, user=self.user)
            response = FormulaSearchView.as_view({"get": "list"})(request)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.data["data"]["ready"])

            request = self.factory.post(
                "/api/cms/llm/rag/search/",
                {
                    "symptoms": ["食少", "便溏", "乏力"],
                    "mechanisms": ["脾胃气虚"],
                    "treatments": ["益气健脾"],
                    "top_k": 3,
                },
                format="json",
            )
            force_authenticate(request, user=self.user)
            response = FormulaSearchView.as_view({"post": "create"})(request)
            self.assertEqual(response.status_code, 200)
            candidate = response.data["data"]["candidates"][0]
            self.assertEqual(candidate["id"], "10001")
            self.assertEqual(candidate["source"]["pdf_pages"], [554])

    def test_empty_search_is_rejected(self):
        request = self.factory.post("/api/cms/llm/rag/search/", {}, format="json")
        force_authenticate(request, user=self.user)
        response = FormulaSearchView.as_view({"post": "create"})(request)
        self.assertEqual(response.status_code, 400)

    def test_authentication_is_required(self):
        request = self.factory.get("/api/cms/llm/rag/search/")
        response = FormulaSearchView.as_view({"get": "list"})(request)
        # Legacy CMS envelope keeps HTTP 200 while returning an explicit auth error code.
        self.assertEqual(response.data["code"], 401)

    def test_workbench_can_request_untruncated_formula_fields(self):
        import sqlite3
        text = '虚构测试原文。' * 800
        with sqlite3.connect(self.index) as db:
            original = db.execute('SELECT indications FROM formulas WHERE id=?', ('10001',)).fetchone()[0]
            db.execute('UPDATE formulas SET indications=? WHERE id=?', (text, '10001'))
        try:
            retriever = FormulaRetriever(self.index)
            brief = retriever.search({'formula_names': ['四君子汤']})['candidates'][0]
            full = retriever.search({'formula_names': ['四君子汤']}, full_fields=True)['candidates'][0]
            self.assertIn('主治', brief['truncated_fields'])
            self.assertEqual(full['fields']['主治'], text)
            self.assertEqual(full['truncated_fields'], [])
        finally:
            with sqlite3.connect(self.index) as db:
                db.execute('UPDATE formulas SET indications=? WHERE id=?', (original, '10001'))

    def test_missing_index_returns_service_unavailable(self):
        with self.settings(RAG_INDEX_PATH=self.index.parent / "missing.sqlite3"):
            request = self.factory.post(
                "/api/cms/llm/rag/search/",
                {"symptoms": ["乏力"]},
                format="json",
            )
            force_authenticate(request, user=self.user)
            response = FormulaSearchView.as_view({"post": "create"})(request)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data["code"], 503)
