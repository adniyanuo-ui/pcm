import datetime
import os
import re
import zipfile

from django.shortcuts import render

# Create your views here.
from patient.models import Patient
from .filters import PatientFilter
from .serializers import PatientSerializer
from tools.resp import get_response
from tools.token_util import token
from tools.viewset import ModelViewSet
from tools.viewset import ModelViewSet
from django.contrib.auth.models import User
from rest_framework.exceptions import APIException, ValidationError, NotAuthenticated

from django.contrib.auth import authenticate

from user.models import UserProfile
from django.db.models import Count
from django.contrib.auth.hashers import make_password


class PatientView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Patient.objects.order_by("-id")
    # queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    filterset_class = PatientFilter

    def get_queryset(self):
        queryset = self.queryset
        if not self.request.user.is_superuser:
            queryset = queryset.filter(doctor_id=self.request.user.id)

        return queryset


class LoginView(ModelViewSet):
    http_method_names = ["post"]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        username = request.data["username"]
        password = request.data["password"]
        user = authenticate(request, username=username, password=password)  # 验证成功之后就会返回这个user对象
        if not user:
            raise ValidationError('认证失败')

        t = token.encode({"user_id": user.id, "username": user.username}, key="cms")
        UserProfile.objects.filter(user_id=user.id).update(token=t)
        result = {
            "account": username,
            "token": t,
        }
        return get_response(result)


class UserView(ModelViewSet):
    http_method_names = ["get"]
    queryset = User.objects.all()
