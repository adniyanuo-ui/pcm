# _*_coding:utf-8_*_
# __author: guo
import re

from rest_framework import serializers

from patient.models import Answer
from question.models import Question


class QuestionSerializer(serializers.ModelSerializer):
    # 大题的名称
    parent_titles = serializers.SerializerMethodField()
    next_id = serializers.SerializerMethodField()
    pre_id = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    def get_parent_titles(self, instance):
        parent = Question.objects.filter(id=instance.parent_id).values_list("title", "title_number", named=1).first()
        num_title = re.findall(r"([一二三四五六七八九十\d.]+)?", instance.title)[0]
        li = num_title.split(".")
        result = [
            {
                "title_number": parent.title_number,
                "title": parent.title,
            }
        ]
        if len(li) >= 3:
            for i in range(len(li) - 2):
                end_idx = len(li) - i - 1
                title_start = ".".join(li[:end_idx])
                sub = Question.objects.filter(title__istartswith=title_start, level=1, order__lt=instance.order) \
                    .values_list("title", "title_number", named=1).first()
                result.append({
                    "title_number": sub.title_number,
                    "title": sub.title,
                })

        return result

    def get_next_id(self, instance):
        obj = Question.objects.filter(id__gt=instance.id, level=1).order_by("id").first()
        if not obj:
            return 0

        return obj.id

    def get_pre_id(self, instance):
        """
        已经答过题，可以查看之前的答案
        """
        obj = Question.objects.filter(id__lt=instance.id, level=1).order_by("-id").first()
        if not obj:
            return 0

        return obj.id

    def get_children(self, instance):
        children = Question.get_deep_data(instance.id,
                                          ["id", "title", "title_number", "mode", "parent_id", "clear_ids"])
        self.context[f"children-{instance.id}"] = children
        return children

    @classmethod
    def deep_children_get_all_answer(cls, li):
        result = {}
        for item in li:
            result[f'{item["id"]}'] = ""
            # if item["mode"] in [2, 4]:
            #     result[f'{item["id"]}'] = ""
            # else:
            #     result[f'{item["id"]}'] = False
            result.update(cls.deep_children_get_all_answer(item.get("children", [])))

        return result

    def get_answer(self, instance):
        answer = self.context["q_id2answer"].get(instance.id, None)
        all_answer = getattr(answer, "all_answer", {})
        if not all_answer:
            # 获取所有选项
            all_answer = self.deep_children_get_all_answer(self.context[f"children-{instance.id}"])
            all_answer[f"{instance.id}"] = ""
        return {f"{k}": v for k, v in all_answer.items()}

    class Meta:
        model = Question
        fields = [
            "id", "title", "parent_titles", "mode", "children", "next_id", "pre_id", "title_number", "answer",
            "clear_ids"
        ]


class OpSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    def get_children(self, instance):
        return Question.objects.filter(parent_id=instance.id).exists()

    class Meta:
        model = Question
        fields = [
            "id", "title", "mode", "children"
        ]
