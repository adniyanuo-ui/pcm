# _*_coding:utf-8_*_
# __author: guo
# from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views

router = SimpleRouter()
router.register(r"medical/record", views.MedicalRecordView, basename="medical/record")

urlpatterns = [
    path(r'', include(router.urls)),
]
