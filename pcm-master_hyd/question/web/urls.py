"""damage_detection URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import include
from . import views
from rest_framework.routers import DefaultRouter
from django.urls import path, include, re_path

router = DefaultRouter()
# 题目
router.register(r"question", views.QuestionView, basename="question")
# 选项
router.register(r"op", views.OpView, basename="op")

urlpatterns = [
    path(r'', include(router.urls)),
    # path('login', views.UserLogin, name='login'),
]
