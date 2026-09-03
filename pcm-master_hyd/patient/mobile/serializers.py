# _*_coding:utf-8_*_
# __author: guo
import os.path
import re

from rest_framework import serializers

from llm.models import Revise
from patient.models import Answer, Patient
from pcm.settings import pdf_dir
from question.models import Question


class PatientSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()

    def get_company(self, instance):
        if instance.q_type != self.context["request"].GET.get("q_type", "common"):
            return ""
        return instance.company

    def get_department(self, instance):
        if instance.q_type != self.context["request"].GET.get("q_type", "common"):
            return ""
        return instance.department

    def get_date(self, instance):
        return f"{instance.date}".split(" ", 1)[0]

    class Meta:
        model = Patient
        fields = [
            "name", "sex", "age", "date", "phone", "marital_status", "job", "origin", "q_type",
            "height", "weight", "blood_type", "blood_sugar", "blood_pressure", "company", "department"
        ]


class HistorySerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()

    def get_date(self, instance):
        return f"{instance.date}".split(" ", 1)[0]

    class Meta:
        model = Patient
        fields = [
            "id", "date", "result", "name"
        ]


class HistoryRetrieveSerializer(serializers.ModelSerializer):
    date = serializers.SerializerMethodField()
    revise_output = serializers.SerializerMethodField()
    prescription = serializers.SerializerMethodField()

    def get_date(self, instance):
        return f"{instance.date}".split(" ", 1)[0]

    def get_revise_output(self, instance):
        result = Revise.objects.filter(p_id=instance.id, uid=0) \
                     .values_list("revise_output", flat=1).order_by("-id").first() or ""
        # result = result.replace("\n\n", "\n")
        return result

    def get_prescription(self, instance):
        result = Revise.objects.filter(p_id=instance.id, uid=0) \
                     .values_list("prescription", flat=1).order_by("-id").first() or ""
        # result = result.replace("\n\n", "\n")
        return result

    class Meta:
        model = Patient
        fields = [
            "id", "date", "result", "revise_output", "prescription"
        ]
