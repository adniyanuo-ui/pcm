"""pcm URL Configuration

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
from django.urls import path
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    # web
    path(r'api/question/', include(('question.web.urls', 'question'), namespace='question')),
    path(r'api/patient/', include(('patient.web.urls', 'patient'), namespace='patient')),
    path(r'api/llm/', include(('llm.web.urls', 'llm'), namespace='llm')),

    # 后台管理系统
    path(r'api/cms/user/', include(('user.cms.urls', 'user'), namespace='cms/user')),
    path(r'api/cms/patient/', include(('patient.cms.urls', 'patient'), namespace='cms/patient')),
    path(r'api/cms/llm/', include(('llm.cms.urls', 'llm'), namespace='cms/llm')),
    path(r'api/cms/system/', include(('system.cms.urls', 'system'), namespace='cms/system')),
    path(r'api/cms/speech/', include(('speech.cms.urls', 'speech'), namespace='cms/speech')),

    # 移动端
    path(r'api/mobile/patient/', include(('patient.mobile.urls', 'patient'), namespace='mobile/patient')),
    path(r'api/mobile/question/', include(('question.mobile.urls', 'question'), namespace='mobile/question')),
    path(r'api/mobile/system/', include(('system.mobile.urls', 'system'), namespace='mobile/system')),

]
