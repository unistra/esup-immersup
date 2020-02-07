# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('course', views.course, name='course'),
    path('courses_list', views.courses_list, name='courses_list'),
    path('mycourses/', views.mycourses, name='mycourses'),
    path('myslots/', views.myslots, name='myslots'),
    path('components/', views.components_list, name='components_list'),
    path('slots/<int:component>/', views.slots_list, name='slots_list'),
    path('slot/add', views.add_slot, name='add_slot'),
    path('slot/modify/<int:slot_id>', views.modify_slot, name='modify_slot'),
    path('slot/delete/<int:slot_id>', views.del_slot, name='delete_slot'),
    path('course/<int:course_id>', views.course, name='modify_course'),
    path('course/<int:course_id>/<int:duplicate>', views.course, name='duplicate_course'),
]
