# _*_coding:utf-8_*_
# __author: guo
import os.path
import re

from rest_framework import serializers

from patient.models import Answer, Patient
from pcm.settings import pdf_dir
from question.models import Question


class PatientSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField()
    q_type = serializers.SerializerMethodField()

    def get_q_type(self, instance):
        q_type = instance.q_type or "common"
        return dict(instance.q_type_choice)[q_type]

    def get_date(self, instance):
        return f"{instance.date}".split(" ", 1)[0]

    def get_file(self, instance):
        return os.path.join(pdf_dir, f"{instance.id}.pdf")

    class Meta:
        model = Patient
        fields = [
            "id", "name", "sex", "age", "date", "phone", "marital_status", "job", "origin", "result", "file",
            "height", "weight", "blood_type", "blood_sugar", "blood_pressure", "q_type", "company", "department",
            "jl_level", "yu_level", "birthday", "nation", "allergy"
        ]
