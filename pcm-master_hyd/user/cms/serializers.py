# _*_coding:utf-8_*_
# __author: guo
from rest_framework import serializers

from patient.models import Patient
from system.models import Scene
from user.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username"
        ]
