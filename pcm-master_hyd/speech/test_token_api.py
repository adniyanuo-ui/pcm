import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from speech.cms.views import TokenView


class SpeechTokenApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = SimpleNamespace(id=1, is_authenticated=True)

    def request(self):
        request = self.factory.post("/api/cms/speech/token/", {}, format="json")
        force_authenticate(request, user=self.user)
        return TokenView.as_view({"post": "create"})(request)

    @override_settings(ALIYUN_NLS_APPKEY="")
    def test_missing_appkey_returns_503(self):
        response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], 503)

    @override_settings(
        ALIYUN_NLS_APPKEY="test-appkey",
        ALIYUN_NLS_GATEWAY="wss://example.test/ws/v1",
    )
    @patch("speech.cms.views.Token.objects.filter")
    @patch("speech.cms.views.Token.ali_speech", return_value="temporary-token")
    def test_returns_only_temporary_browser_credentials(self, _, token_filter):
        token_filter.return_value.first.return_value = SimpleNamespace(
            expire_time=datetime.datetime(2026, 9, 4, 12, 0, 0)
        )
        response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"],
            {
                "token": "temporary-token",
                "appkey": "test-appkey",
                "gateway": "wss://example.test/ws/v1",
                "expires_at": "2026-09-04T12:00:00",
            },
        )
