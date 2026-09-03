# _*_coding:utf-8_*_
# __author: guo
from rest_framework import status
from rest_framework.response import Response


def get_response(data='', code=200, msg='success', status_code=status.HTTP_200_OK, **kwargs):
    result = {
        "code": code,
        "msg": msg,
        "data": data,
    }
    result.update(kwargs)
    return Response(result, status=status_code)
