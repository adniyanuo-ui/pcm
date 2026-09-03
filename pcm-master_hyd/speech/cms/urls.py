# _*_coding:utf-8_*_
# __author: guo
# from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r"token", views.TokenView, basename="token")
router.register(r"speech", views.SpeechView, basename="speech")

urlpatterns = [
    path(r'', include(router.urls)),
]
