import base64
import datetime
import json

import requests
import qrcode
from django.db import models

# Create your models here.
from pcm.settings import wx_env, ALI_AK, ALI_AK_SECRET, HOST
from tools.base_model import BaseModel
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest

from tools.utils import pil_to_base64


class Scene(BaseModel):
    # scene = id
    data = models.JSONField(verbose_name="微信二维码用scene获取的数据", default=dict)

    img = models.TextField(verbose_name="img base64", default="")

    remark = models.CharField(verbose_name="备注", default="", max_length=1024)

    class Meta:
        verbose_name = "微信二维码表"

    @classmethod
    def gen_wx_qr(cls, data, access_token, remark):
        obj = cls.objects.create(data=data, remark=remark)
        payload = {
            "scene": f"{obj.id}",
            "page": "pages/survey_table/survey/welcome/index",
            "env_version": wx_env,
            "check_path": False
        }
        resp = requests.post(
            f"https://api.weixin.qq.com/wxa/getwxacodeunlimit?access_token={access_token}",
            json=payload
        )
        base64_data = base64.b64encode(resp.content)
        bs64 = base64_data.decode('utf-8')
        bs64 = f"data:image/jpeg;base64,{bs64}"

        cls.objects.filter(id=obj.id).update(img=bs64)

    @classmethod
    def gen_web_qr(cls, data, remark):
        doctor_id = data["doctor_id"]
        url = f"{HOST}/#/user?id={doctor_id}"
        img = qrcode.make(url)
        bs64 = pil_to_base64(img)
        cls.objects.create(data=data, remark=remark, img=bs64)


class Agreement(BaseModel):
    key = models.CharField(verbose_name="key", default="", max_length=32)
    text = models.TextField(verbose_name="协议内容", default="")

    class Meta:
        verbose_name = "用户/隐私协议"


class Token(BaseModel):
    key = models.CharField(verbose_name="key", default="", max_length=32, unique=True)
    token = models.CharField(verbose_name="token", default="", max_length=1024)
    expire_time = models.DateTimeField(verbose_name="过期时间")

    class Meta:
        verbose_name = "别的平台token管理"

    @classmethod
    def ali_speech(cls):
        """
        阿里云智能语音交互
        """
        key = "ali_speech"
        obj = cls.objects.filter(key=key).first()
        if obj and obj.expire_time > datetime.datetime.now() - datetime.timedelta(hours=1):
            return obj.token

        client = AcsClient(ALI_AK, ALI_AK_SECRET, "cn-shanghai")

        request = CommonRequest()
        request.set_method('POST')
        request.set_domain('nls-meta.cn-shanghai.aliyuncs.com')
        request.set_version('2019-02-28')
        request.set_action_name('CreateToken')

        token = ""
        try:
            response = client.do_action_with_exception(request)

            jss = json.loads(response)
            token = jss['Token']['Id']
            expire_time = jss['Token']['ExpireTime']
            # 转换时间
            expire_time = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(expire_time))

            cls.objects.update_or_create(key=key, defaults=dict(token=token, expire_time=expire_time))
        except Exception as e:
            print(e)

        return token
