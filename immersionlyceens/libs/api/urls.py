# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path
from . import views

urlpatterns = [
    path('get_person', views.ajax_get_person, name='PersonByName'),
]
