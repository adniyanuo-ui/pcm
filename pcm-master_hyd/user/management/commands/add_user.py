import random
import string

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

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
        username = options["username"]
        password = "".join(random.sample(string.ascii_letters + string.digits, 8))
        user = User.objects.create_user(username, password=password, is_superuser=0)
        UserProfile.objects.create(user_id=user.id, )
        print(username, password, user.id)
        print("------------end---------------")

    def add_arguments(self, parser):
        parser.add_argument("username")
