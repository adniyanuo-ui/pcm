# _*_coding:utf-8_*_
# __author: guo
from rest_framework import serializers

from patient.models import Patient
from system.models import Scene
from user.models import User


class QrSerializer(serializers.ModelSerializer):
    q_type = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()

    def get_q_type(self, instance):
        q_type = instance.data.get("q_type", "")
        return dict(Patient.q_type_choice).get(q_type, "")

    def get_doctor(self, instance):
        doctor_id = instance.data.get("doctor_id", 0) or 0
        return User.objects.filter(id=doctor_id).values_list("username", flat=1).first() or ""

    class Meta:
        model = Scene
        fields = [
            "id", "data", "remark", "img", "doctor", "q_type"
        ]
