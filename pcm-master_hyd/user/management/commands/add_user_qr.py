import random
import string

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from system.models import Scene
from user.models import UserProfile


class Command(BaseCommand):
    """
    dev:
        test Gsfo2MSm
    prod:
        admin Nw3mx76q
        测试账号0 yNML7VcA
        测试账号1 5T6rcD4V
        测试账号2 RZ42mQCl
        测试账号3 VZA4pDQP
        测试账号4 VpXN9dEj
        测试账号5 xCX0ciNe
    """

    def handle(self, *args, **options):
        for user in User.objects.all():
            if Scene.objects.filter(data__doctor_id=user.id).exists():
                # print(user.username)
                continue
            remark = user.username
            data = {"doctor_id": user.id}
            Scene.gen_web_qr(data, remark)
