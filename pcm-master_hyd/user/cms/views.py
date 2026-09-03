import datetime
import os
import re
import zipfile

from django.shortcuts import render

from system.models import Scene
# Create your views here.
from tools.resp import get_response
from tools.token_util import token
from tools.viewset import ModelViewSet
from tools.viewset import ModelViewSet
from django.contrib.auth.models import User
from rest_framework.exceptions import APIException, ValidationError, NotAuthenticated

from django.contrib.auth import authenticate

from user.cms.serializers import UserSerializer
from user.models import UserProfile
from django.db.models import Count
from django.contrib.auth.hashers import make_password


class RegisterView(ModelViewSet):
    http_method_names = ["post"]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        username = request.data["username"]
        password = request.data["password"]
        if User.objects.filter(username=username).exists():
            raise APIException("已存在的用户名")
        user = User.objects.create_user(username, password=password, is_superuser=0)
        UserProfile.objects.create(user_id=user.id, )

        remark = username
        data = {"doctor_id": user.id}
        Scene.gen_web_qr(data, remark)

        return get_response(msg="注册成功")


class LoginView(ModelViewSet):
    http_method_names = ["post"]
    authentication_classes = []

    def create(self, request, *args, **kwargs):
        username = request.data["username"]
        password = request.data["password"]
        user = authenticate(request, username=username, password=password)  # 验证成功之后就会返回这个user对象
        if not user:
            raise APIException('认证失败')

        t = token.encode({"user_id": user.id, "username": user.username}, key="cms")
        UserProfile.objects.filter(user_id=user.id).update(token=t)
        result = {
            "account": username,
            "token": t,
            "id": user.id,
        }
        return get_response(result)


class UserView(ModelViewSet):
    http_method_names = ["get"]
    queryset = User.objects
    serializer_class = UserSerializer
