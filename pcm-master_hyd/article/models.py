from django.db import models

# Create your models here.
from tools.base_model import BaseModel


class Article(BaseModel):
    title = models.CharField(verbose_name="标题", max_length=1024, default="")
    cover = models.CharField(verbose_name="主图url", max_length=1024, default="")
    content = models.TextField(verbose_name="内容", default="")

    source = models.CharField(verbose_name="来源", max_length=1024, default="")

    uid = models.BigIntegerField(verbose_name="用户id", default=0)

    class Meta:
        verbose_name = "文章表"
