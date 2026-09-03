import base64
import datetime
import json
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


class TokenView(ModelViewSet):
    http_method_names = ["post"]
    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    def create(self, request, *args, **kwargs):
        token = Token.ali_speech()

        return get_response(data={"token": token})


class SpeechView(ModelViewSet):
    http_method_names = ["post"]
    url = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/asr"

    def create(self, request, *args, **kwargs):
        audio = request.data.get('audio')
        audio_bytes = base64.b64decode(audio)
        # with open(f"debug_audio_{time.time()}.pcm", "wb") as f:
        #     f.write(audio_bytes)
        token = Token.ali_speech()
        params = {
            "appkey": "v3PI571WtmAIFlXc",
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
