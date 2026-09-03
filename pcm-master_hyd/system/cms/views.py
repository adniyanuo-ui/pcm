import requests

from pcm.settings import get_access_token, app_id, app_secret
from system.cms.serializers import QrSerializer
from system.models import Scene
from tools.resp import get_response
from tools.viewset import ModelViewSet


class QrView(ModelViewSet):
    """小程序"""
    http_method_names = ["post", "get", "delete"]
    queryset = Scene.objects.all()
    serializer_class = QrSerializer

    def create(self, request, *args, **kwargs):
        remark = request.data["remark"]
        data = request.data["data"]
        params = {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
        resp = requests.get(get_access_token, params=params)
        access_token = resp.json()["access_token"]
        Scene.gen_wx_qr(data, access_token, remark)

        return get_response(msg="创建成功")


class QrWebView(ModelViewSet):
    http_method_names = ["post", "get", "delete"]
    queryset = Scene.objects.all()
    serializer_class = QrSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(data__doctor_id=self.request.user.id)

        return queryset

    def create(self, request, *args, **kwargs):
        remark = request.data["remark"]
        data = request.data["data"]
        Scene.gen_web_qr(data, remark)

        return get_response(msg="创建成功")
