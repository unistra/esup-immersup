from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from . import views

urlpatterns = [
    path('courses_list', views.courses_list, name='courses_list'),
]