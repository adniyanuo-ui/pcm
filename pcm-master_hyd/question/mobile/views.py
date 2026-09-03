import copy

from django.shortcuts import render

# Create your views here.
from patient.models import Answer
from .filters import QuestionFilter
from question.models import Question
from .serializers import QuestionSerializer, OpSerializer
from tools.resp import get_response
from tools.viewset import ModelViewSet


class QuestionView(ModelViewSet):
    authentication_classes = []
    http_method_names = ["get"]
    queryset = Question.objects.filter(level=1)
    serializer_class = QuestionSerializer

    # filterset_class = QuestionFilter

    def get_object(self):
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        pk = self.kwargs[lookup_url_kwarg]
        if int(pk) == 0:
            obj = Question.objects.filter(level=1).order_by("id").first()
        else:
            obj = Question.objects.filter(level=1, id=pk).first()

        return obj

    def get_serializer(self, queryset_or_obj, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        if self.action == "list":
            kwargs.setdefault('context', self.get_serializer_context(queryset_or_obj))
        else:
            kwargs.setdefault('context', self.get_serializer_context([queryset_or_obj]))
        return serializer_class(queryset_or_obj, *args, **kwargs)

    def get_serializer_context(self, queryset):
        result = super(QuestionView, self).get_serializer_context()

        patient_id = self.request.GET.get("patient_id", "0")
        q_ids = [x.id for x in queryset]

        q_id2answer = {}
        for obj in Answer.objects.filter(p_id=patient_id, q_id__in=q_ids):
            q_id2answer[obj.q_id] = obj

        result["q_id2answer"] = q_id2answer
        result["q_id2q"] = q_id2answer
        return result
