from django.db import models

# Create your models here.
from tools.base_model import BaseModel
from django.contrib.auth.models import User


class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    token = models.CharField(max_length=256, default="")

    class Meta:
        verbose_name = "User profile"
