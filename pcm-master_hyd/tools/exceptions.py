# -*- coding: utf-8 -*-
from rest_framework.response import Response
from rest_framework import exceptions
from django.conf import settings

from pcm.settings import DEBUG
from tools.resp import get_response


def custom_exception_handler(exc, context):
    if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        return get_response(code=401, msg=f"{exc}")
    elif isinstance(exc, exceptions.APIException):
        return get_response(code=500, msg=f"{exc}")

    if not DEBUG:
        return get_response(code=500, msg=str(exc))
