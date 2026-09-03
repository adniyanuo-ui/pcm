import datetime
import json
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from system.models import Token


class AliSpeechTokenTests(TestCase):
    @override_settings(ALI_AK="", ALI_AK_SECRET="")
    def test_missing_credentials_are_reported(self):
        with self.assertRaises(ImproperlyConfigured):
            Token.ali_speech()

    @patch("system.models.AcsClient")
    def test_valid_cached_token_does_not_call_aliyun(self, client_class):
        Token.objects.create(
            key="ali_speech",
            token="cached-token",
            expire_time=datetime.datetime.now() + datetime.timedelta(minutes=30),
        )
        self.assertEqual(Token.ali_speech(), "cached-token")
        client_class.assert_not_called()

    @override_settings(
        ALI_AK="test-access-key",
        ALI_AK_SECRET="test-access-secret",
        ALIYUN_NLS_REGION="cn-shanghai",
    )
    @patch("system.models.AcsClient")
    def test_expiring_token_is_refreshed(self, client_class):
        Token.objects.create(
            key="ali_speech",
            token="old-token",
            expire_time=datetime.datetime.now() + datetime.timedelta(minutes=2),
        )
        expires = datetime.datetime.now() + datetime.timedelta(hours=12)
        client_class.return_value.do_action_with_exception.return_value = json.dumps(
            {
                "Token": {
                    "Id": "fresh-token",
                    "ExpireTime": int(expires.timestamp()),
                }
            }
        ).encode()

        self.assertEqual(Token.ali_speech(), "fresh-token")
        record = Token.objects.get(key="ali_speech")
        self.assertEqual(record.token, "fresh-token")
        self.assertGreater(record.expire_time, datetime.datetime.now())
