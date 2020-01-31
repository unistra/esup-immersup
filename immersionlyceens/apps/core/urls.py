# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path
from . import views

urlpatterns = [
    path('components/', views.list_of_components, name='components_list'),
    path('components/<int:component>/', views.list_of_slots, name='slots_list'),
]
