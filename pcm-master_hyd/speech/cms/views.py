import base64
import datetime
import json
import logging
import time
import uuid

from llm.cms.serializers import ReviseSerializer, ShowChatSerializer, ShowChatOneSerializer
from llm.models import Revise, Record
from llm_utils.client import model_name2client
from llm_utils.prompt import v1
from patient.models import Patient, Answer
from system.models import Token
from tools.resp import get_response
from tools.viewset import ModelViewSet
from django.http import StreamingHttpResponse
import requests
from django.conf import settings
from rest_framework import status


logger = logging.getLogger(__name__)


class TokenView(ModelViewSet):
    http_method_names = ["post"]
    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    def create(self, request, *args, **kwargs):
        if not settings.ALIYUN_NLS_APPKEY:
            return get_response(
                code=503,
                msg="语音服务尚未配置 ALIYUN_NLS_APPKEY",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            token = Token.ali_speech()
            token_record = Token.objects.filter(key="ali_speech").first()
        except Exception:
            logger.exception("Failed to obtain Aliyun NLS token")
            return get_response(
                code=502,
                msg="暂时无法连接语音识别服务，请稍后重试",
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return get_response(
            data={
                "token": token,
                "appkey": settings.ALIYUN_NLS_APPKEY,
                "gateway": settings.ALIYUN_NLS_GATEWAY,
                **({'vocabulary_id': settings.ALIYUN_NLS_VOCABULARY_ID} if settings.ALIYUN_NLS_VOCABULARY_ID else {}),
                "expires_at": token_record.expire_time.isoformat() if token_record else "",
            }
        )


class SpeechView(ModelViewSet):
    http_method_names = ["post"]
    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    def create(self, request, *args, **kwargs):
        if not settings.ALIYUN_NLS_APPKEY:
            return get_response(
                code=503,
                msg="语音服务尚未配置 ALIYUN_NLS_APPKEY",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        audio = request.data.get('audio')
        audio_bytes = base64.b64decode(audio)
        # with open(f"debug_audio_{time.time()}.pcm", "wb") as f:
        #     f.write(audio_bytes)
        token = Token.ali_speech()
        params = {
            "appkey": settings.ALIYUN_NLS_APPKEY,
            "format": "pcm",
            "sample_rate": "16000",
            "enable_punctuation_prediction": "true",
            "enable_inverse_text_normalization": "true",
        }
        headers = {
            "X-NLS-Token": token,
            "Content-Type": "application/octet-stream",
            "Host": "nls-gateway-cn-shanghai.aliyuncs.com",
        }
        resp = requests.post(self.url, params=params, headers=headers, data=audio_bytes)

        return get_response(data=resp.json())
