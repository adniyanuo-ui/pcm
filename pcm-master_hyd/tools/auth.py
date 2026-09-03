# _*_coding:utf-8_*_
# __author: guo
import rest_framework
from rest_framework.authentication import BaseAuthentication

from patient.models import Patient, People
from tools.token_util import token
from django.contrib.auth.models import User
from rest_framework.exceptions import APIException, ValidationError, AuthenticationFailed
from django.utils.translation import gettext_lazy as _


class TokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        auth = auth.replace("Token ", "")
        if not auth:
            raise AuthenticationFailed('认证失败')

        key = "web"
        if "/cms/" in request.path:
            key = "cms"
        elif "/mobile/" in request.path:
            key = "mobile"

        try:
            payload = token.decode(auth, key)
        except Exception as e:
            raise AuthenticationFailed('认证失败')

        if key == "web":
            return self.web_authenticate(auth, payload)
        elif key == "mobile":
            return self.mobile_authenticate(auth, payload)
        else:
            return self.cms_authenticate(auth, payload)

    def cms_authenticate(self, auth, payload):
        try:
            uid = payload["user_id"]
            user = User.objects.filter(id=uid, profile__token=auth).first()
            if not user:
                raise AuthenticationFailed("认证失败")

            return user, auth
        except Exception as e:
            raise AuthenticationFailed("认证失败")

    def web_authenticate(self, auth, payload):
        try:
            uid = payload["user_id"]
            people = People.objects.filter(id=uid, token=auth).first()
            # web 由于之前写好的逻辑都是用的Patient，所以做一下转换
            user = Patient.objects.filter(people_id=people.id).order_by("-id").first()
            if not user:
                raise AuthenticationFailed("认证失败")

            return user, auth
        except Exception as e:
            raise AuthenticationFailed("认证失败")

    def mobile_authenticate(self, auth, payload):
        try:
            uid = payload["user_id"]
            user = People.objects.filter(id=uid, token=auth).first()
            if not user:
                raise AuthenticationFailed("认证失败")

            return user, auth
        except Exception as e:
            raise AuthenticationFailed("认证失败")
