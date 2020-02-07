# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('get_person', views.ajax_get_person, name='PersonByName'),
    path('get_available_vars/<int:template_id>', views.ajax_get_available_vars,
         name='GetAvailableVars'),
    path('get_courses/<int:component_id>/', views.ajax_get_courses, name='GetCourses'),
    path('get_available_documents/', views.get_ajax_documents, name='get_available_documents'),
    path('get_slots/<int:component>', views.get_ajax_slots, name='get_slots',),
    path('get_trainings', views.ajax_get_trainings, name='GetTrainings'),
    path('get_available_documents/', views.get_ajax_documents, name='get_available_documents',),
    path('get_courses_by_training/<int:training_id>', views.ajax_get_courses_by_training,
         name='get_courses_training',),
    path('get_buildings/<int:campus_id>', views.ajax_get_buildings, name='get_buildings',),
    path('get_course_teachers/<int:course_id>', views.ajax_get_course_teachers,
         name='get_course_teachers',),
]
