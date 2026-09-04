from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from llm.cms.views import ChatView, GenDialogueView


class DefaultModelTests(SimpleTestCase):
    @override_settings(DEFAULT_LLM_MODEL="deepseek-v4-pro")
    @patch.object(GenDialogueView, "gen", return_value=iter(()))
    def test_dialogue_generation_defaults_to_deepseek(self, mocked_gen):
        request = SimpleNamespace(data={"text": "测试医患对话"})

        GenDialogueView().create(request)

        self.assertEqual(mocked_gen.call_args.args[1], "deepseek-v4-pro")

    @override_settings(DEFAULT_LLM_MODEL="deepseek-v4-pro")
    @patch.object(ChatView, "gen", return_value=iter(()))
    def test_clinical_draft_defaults_to_deepseek(self, mocked_gen):
        request = SimpleNamespace(
            user=SimpleNamespace(id=7),
            data={
                "patient_id": 1,
                "user": "患者基本信息",
                "question": "问诊信息",
                "dialogue": "医患对话",
                "doctor": "四诊补充",
            },
        )

        ChatView().create(request)

        self.assertEqual(mocked_gen.call_args.args[-1], "deepseek-v4-pro")
