import re

from django.db import models
from cn2an import cn2an
# Create your models here.
from tools.base_model import BaseModel
from mptt.models import MPTTModel, TreeForeignKey


class Question(BaseModel, MPTTModel):
    mode_choice = [
        (-1, "不需要选项"),
        (0, "是/否"),
        (1, "单选空"),
        (2, "短文本输入框"),
        (3, "多选"),
        (4, "长文本输入框"),
    ]
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')

    title = models.TextField(verbose_name="题目", default="")
    title_number = models.CharField(verbose_name="题号", default="", max_length=128)

    # 废弃
    title_level = models.IntegerField(verbose_name="题号等级", default=0)

    order = models.IntegerField(verbose_name="题目顺序，每一级都有", default=0)

    # {"level": 0, "type": "定性"}
    jl = models.JSONField(verbose_name="焦虑", default=dict)
    yu = models.JSONField(verbose_name="抑郁", default=dict)

    mode = models.IntegerField(verbose_name="题目类型", default=0)
    clear_ids = models.JSONField(verbose_name="选择了这一题，需要清除哪些选项", default=list)

    class Meta:
        verbose_name = "试题"
        indexes = [
            models.Index(fields=['level', 'order'], name='level_order'),
        ]

    @classmethod
    def add_q_20250427(cls):
        obj_17 = cls.objects.create(parent=None, title="补充症状", title_number="十七", mode=-1)
        obj = cls.objects.create(parent=obj_17, title="既往病史", title_number="17.1", mode=-1)
        cls.objects.create(parent=obj, title="", title_number="", mode=2)

        obj_18 = cls.objects.create(parent=None, title="日常描述", title_number="十八", mode=-1)
        obj = cls.objects.create(parent=obj_18, title="生活习惯(有利于大夫给医嘱)", title_number="18.1", mode=-1)
        cls.objects.create(parent=obj, title="", title_number="", mode=2)

    @classmethod
    def get_all_question(cls):
        id2item = {}
        for item in cls.objects.values("id", "parent_id", "title", "title_number", "mode", "order", "level") \
                .order_by("parent_id", "order"):
            id2item[item["id"]] = item

        result = []
        for item in id2item.values():
            if item["parent_id"] is None:
                item["parent"] = "0"
                result.append(item)
                continue

            parent_item = id2item[item["parent_id"]]
            item["parent"] = f"{parent_item['parent']}-{item['parent_id']}"
            parent_item.setdefault("children", []).append(item)

        return id2item

    @classmethod
    def get_deep_data(cls, parent_id, fields=None):
        assert isinstance(fields, list)

        result = []
        queryset = cls.objects.filter(parent_id=parent_id).values(*fields).order_by("id")
        for item in queryset:
            item["children"] = cls.get_deep_data(item["id"], fields)
            result.append(item)

        return result

# class Option(BaseModel):
#     q = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="op")
#     title = models.CharField(verbose_name="选项名称", max_length=256, default="")
#     source = models.CharField(verbose_name="来源", max_length=256, default="")
#
#     class Meta:
#         verbose_name = "选项"
