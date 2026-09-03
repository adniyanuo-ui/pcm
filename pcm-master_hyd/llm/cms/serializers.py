# _*_coding:utf-8_*_
# __author: guo
import json
import os.path
import re

from rest_framework import serializers

from llm.models import Revise, Record
from llm_utils.client import model_name2name
from patient.models import Answer, Patient
from pcm.settings import pdf_dir
from question.models import Question


class ReviseSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()
    dialogue = serializers.SerializerMethodField()
    revise_case = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()
    output = serializers.SerializerMethodField()
    reasoning = serializers.SerializerMethodField()
    created_time = serializers.SerializerMethodField()
    patient_id = serializers.SerializerMethodField()
    model_name = serializers.SerializerMethodField()
    output_over = serializers.SerializerMethodField()
    edit = serializers.SerializerMethodField()
    star_str = serializers.SerializerMethodField()

    def get_user(self, instance):
        if instance.user:
            return instance.user

        return Revise.init_user(instance.p)

    def get_question(self, instance):
        if instance.question:
            return instance.question

        return Revise.init_question(instance.p)

    def get_doctor(self, instance):
        if instance.doctor:
            return instance.doctor

        return Revise.init_doctor(instance.p)

    def get_dialogue(self, instance):
        if instance.dialogue:
            return instance.dialogue

        return Revise.init_dialogue(instance.p)

    def get_revise_case(self, instance):
        if instance.revise_case:
            return instance.revise_case

        return Revise.init_revise_case(instance.p)

    def get_output(self, instance):
        if instance.id:
            return instance.revise_output or instance.r.output

        return ""

    def get_reasoning(self, instance):
        if instance.id:
            return instance.r.reasoning

        return ""

    def get_created_time(self, instance):
        return instance.created_time.__str__().split(".", 1)[0]

    def get_patient_id(self, instance):
        return instance.p_id

    def get_model_name(self, instance):
        if instance.id:
            return model_name2name[instance.r.model_name]

        return ""

    def get_output_over(self, instance):
        return bool(instance.id)

    def get_edit(self, instance):
        return False

    def get_star_str(self, instance):
        return "⭐️" * instance.star

    class Meta:
        model = Revise
        fields = [
            "id", "user", "doctor", "output", "created_time", "reasoning", "patient_id", "star", "model_name",
            "output_over", "edit", "star_str", "question", "dialogue", "revise_case"
        ]


class ShowChatSerializer(serializers.ModelSerializer):
    patient = serializers.SerializerMethodField()
    star = serializers.SerializerMethodField()
    model_name = serializers.SerializerMethodField()
    runtime = serializers.SerializerMethodField()
    prompt_tokens = serializers.SerializerMethodField()
    completion_tokens = serializers.SerializerMethodField()

    def get_patient(self, instance):
        return instance.p.name

    def get_star(self, instance):
        return "⭐️" * instance.star

    def get_model_name(self, instance):
        return instance.r.model_name

    def get_runtime(self, instance):
        return instance.r.runtime

    def get_prompt_tokens(self, instance):
        return instance.r.prompt_tokens

    def get_completion_tokens(self, instance):
        return instance.r.completion_tokens

    class Meta:
        model = Revise
        fields = [
            "id", "r_id", "star", "revise_output", "patient", "model_name", "runtime", "prompt_tokens",
            "completion_tokens"
        ]


class ShowChatOneSerializer(serializers.ModelSerializer):
    system = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    revise_output = serializers.SerializerMethodField()

    def get_system(self, instance):
        return json.loads(instance.messages)[0]["content"]

    def get_user(self, instance):
        return json.loads(instance.messages)[1]["content"]

    def get_revise_output(self, instance):
        revise_output = Revise.objects.filter(r_id=instance.id).values_list("revise_output", flat=1).first() or ""
        if revise_output == instance.output:
            return ""
        else:
            return revise_output

    class Meta:
        model = Record
        fields = [
            "id", "model_name", "runtime", "output", "system", "reasoning", "user", "revise_output"
        ]
