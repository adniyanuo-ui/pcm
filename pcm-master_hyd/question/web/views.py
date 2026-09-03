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
    # authentication_classes = []
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

        user = self.request.user
        q_ids = [x.id for x in queryset]

        q_id2answer = {}
        for obj in Answer.objects.filter(p=user, q_id__in=q_ids):
            q_id2answer[obj.q_id] = obj

        result["q_id2answer"] = q_id2answer
        result["q_id2q"] = q_id2answer
        return result


class OpView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Question.objects.filter(level__gt=1)

    # serializer_class = OpSerializer

    def get_queryset(self):
        parent_id = self.request.GET["parent_id"]
        return self.queryset.filter(parent_id=parent_id).order_by("order")

    def deep_get_op(self, queryset):
        result = []

        ids = [x.id for x in queryset]
        id2children = {}
        for obj in Question.objects.filter(parent_id__in=ids).values_list("parent_id", "id", named=1):
            id2children[obj.parent_id] = bool(obj.id)

        for obj in queryset:
            children_exist = id2children.get(obj.id, False)
            tmp = {
                "id": obj.id,
                "parent_id": obj.parent_id,
                "title": obj.title,
                "title_number": obj.title_number,
                "mode": obj.mode,
                # "children": [],
                "children_exist": children_exist,
            }
            result.append(tmp)
            if obj.mode == -1 and children_exist:
                children_queryset = Question.objects.filter(parent_id=obj.id).order_by("order")
                result.extend(self.deep_get_op(children_queryset))

        return result

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        result = self.deep_get_op(queryset)
        return get_response(result)
