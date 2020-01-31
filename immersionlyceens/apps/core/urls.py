# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path
from . import views

urlpatterns = [
    path('components/', views.list_of_components, name='components_list'),
    path('components/<int:component>/', views.list_of_slots, name='slots_list'),
    path('slot/add', views.add_slot, name='add_slot'),
    path('slot/modify/<int:slot_id>', views.modify_slot, name='modify_slot'),
    path('slot/delete:<int:slot_id>', views.del_slot, name='delete_slot'),
    path('courses_list', views.courses_list, name='courses_list'),
]