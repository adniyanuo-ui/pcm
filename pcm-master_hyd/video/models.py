from django.db import models

# Create your models here.
from tools.base_model import BaseModel


class Video(BaseModel):
    title = models.CharField(verbose_name="标题", max_length=1024, default="")
    cover = models.CharField(verbose_name="主图url", max_length=1024, default="")
    link = models.CharField(verbose_name="视频链接", max_length=1024, default="")

    source = models.CharField(verbose_name="来源", max_length=1024, default="")

    uid = models.BigIntegerField(verbose_name="用户id", default=0)

    class Meta:
        verbose_name = "视频表"
