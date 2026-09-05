# _*_coding:utf-8_*_
# __author: guo
# from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views
from llm.encounters import EncounterView

router = SimpleRouter()
router.register(r"encounters", EncounterView, basename="encounters")
router.register(r"revise", views.ReviseView, basename="revise")
router.register(r"chat", views.ChatView, basename="chat")
router.register(r"show/chat", views.ShowChatView, basename="show/chat")
router.register(r"gen/dialogue", views.GenDialogueView, basename="gen/dialogue")
router.register(r"gen/case", views.GaseView, basename="gen/case")
router.register(r"rag/search", views.FormulaSearchView, basename="rag/search")
# router.register(r"user", views.UserView, basename="user")

urlpatterns = [
    path(r'', include(router.urls)),
]
