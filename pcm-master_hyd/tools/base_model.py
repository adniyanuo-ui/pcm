from django.db import models
from django.db import connection


class MyDateTimeField(models.DateTimeField):
    def pre_save(self, model_instance, add):
        if add and getattr(model_instance, self.attname):
            return getattr(model_instance, self.attname)

        return super(MyDateTimeField, self).pre_save(model_instance, add)


class BaseModel(models.Model):
    created_time = MyDateTimeField('创建时间', auto_now_add=True)
    updated_time = MyDateTimeField('更新时间', auto_now=True)

    deleted = models.BooleanField(verbose_name="是否删除", default=False)

    class Meta:
        abstract = True
