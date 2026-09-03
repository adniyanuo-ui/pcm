# _*_coding:utf-8_*_
# __author: guo
import os.path
import re

from rest_framework import serializers

from article.models import Article
from patient.models import Answer, Patient
from pcm.settings import pdf_dir
from question.models import Question


class ArticleSerializer(serializers.ModelSerializer):
    created_time = serializers.SerializerMethodField()

    def get_created_time(self, instance):
        return instance.created_time.__str__().replace("T", " ").rsplit(".", 1)[0]

    class Meta:
        model = Article
        fields = [
            "id", "created_time", "title", "cover", "content", "source"
        ]
