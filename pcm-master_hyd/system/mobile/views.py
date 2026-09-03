from system.mobile.serializers import QrSerializer
from system.models import Scene, Agreement
from tools.resp import get_response
from tools.viewset import ModelViewSet


class QrView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Scene.objects
    serializer_class = QrSerializer


class AgreementView(ModelViewSet):
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        key = request.GET["key"]
        txt = Agreement.objects.filter(key=key).values_list("text", flat=True).first()
        return get_response(txt)
