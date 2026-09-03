# _*_coding:utf-8_*_
# __author: guo
# from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r"article", views.ArticleView, basename="article")
# router.register(r"user", views.UserView, basename="user")

urlpatterns = [
    path(r'', include(router.urls)),
]
