# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('get_available_documents/', views.get_ajax_documents, name='get_available_documents'),
    path(
        'get_available_vars/<int:template_id>',
        views.ajax_get_available_vars,
        name='GetAvailableVars',
    ),
    path('get_courses/<int:component_id>/', views.ajax_get_courses, name='GetCourses'),
    path('delete_course', views.ajax_delete_course, name='DeleteCourses'),
    path('get_my_courses/<int:user_id>/', views.ajax_get_my_courses, name='GetMyCourses'),
    path('get_my_slots/<int:user_id>/', views.ajax_get_my_slots, name='GetMySlots'),
    path('get_my_slots/all/<int:user_id>/', views.ajax_get_my_slots, name='GetMySlotsAll'),
    path('get_person', views.ajax_get_person, name='PersonByName'),
    path('get_slots/<int:component>', views.get_ajax_slots, name='get_slots'),
    path('get_trainings', views.ajax_get_trainings, name='GetTrainings'),
]
