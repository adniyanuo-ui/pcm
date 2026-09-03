# _*_coding:utf-8_*_
# __author: guo
from rest_framework import serializers

from system.models import Scene


class QrSerializer(serializers.ModelSerializer):
    class Meta:
        model = Scene
        fields = [
            "data"
        ]
