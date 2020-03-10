# -*- coding: utf-8 -*-

"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('check_vacations', views.ajax_check_date_between_vacation, name='CheckVacations'),
    path('delete_course', views.ajax_delete_course, name='DeleteCourses'),
    path('get_agreed_highschools', views.ajax_get_agreed_highschools, name='GetAgreedHighSchools'),
    path('get_available_documents/', views.get_ajax_documents, name='get_available_documents',),
    path('get_available_documents/', views.get_ajax_documents, name='get_available_documents'),
    path(
        'get_available_vars/<int:template_id>',
        views.ajax_get_available_vars,
        name='GetAvailableVars',
    ),
    path('get_buildings/<int:campus_id>', views.ajax_get_buildings, name='get_buildings',),
    path('get_courses/<int:component_id>/', views.ajax_get_courses, name='GetCourses'),
    path(
        'get_courses_by_training/<int:training_id>',
        views.ajax_get_courses_by_training,
        name='get_courses_training',
    ),
    path(
        'get_course_teachers/<int:course_id>',
        views.ajax_get_course_teachers,
        name='get_course_teachers',
    ),
    path(
        'get_courses_by_training/<int:component_id>/<int:training_id>',
        views.ajax_get_courses_by_training,
        name='get_courses_training',
    ),
    path('get_courses/<int:component_id>/', views.ajax_get_courses, name='GetCourses'),
    path('get_my_courses/<int:user_id>/', views.ajax_get_my_courses, name='GetMyCourses'),
    path('get_my_slots/<int:user_id>/', views.ajax_get_my_slots, name='GetMySlots'),
    path('get_my_slots/all/<int:user_id>/', views.ajax_get_my_slots, name='GetMySlotsAll'),
    path('get_person', views.ajax_get_person, name='PersonByName'),
    path('get_slots', views.get_ajax_slots, name='get_slots',),
    path('get_student_records/', views.ajax_get_student_records, name='GetStudentRecords'),
    path('get_slots_by_course/<int:course_id>', views.ajax_get_slots_by_course, name='get_slots_by_course'),
    path('get_trainings', views.ajax_get_trainings, name='GetTrainings'),
    path('get_immersions/<int:user_id>/<immersion_type>', views.ajax_get_immersions, name='get_immersions'),
    path('get_other_registrants/<int:immersion_id>', views.ajax_get_other_registrants, name='get_other_registrants'),
    # VALIDATE / REJECT ACTION
    path('reject_student/', views.ajax_reject_student, name='rejectStudent'),
    path('validate_student/', views.ajax_validate_student, name='validateStudent'),
    path('check_course_publication/<int:course_id>', views.ajax_check_course_publication,
         name='checkCoursePublication'),
    
    path('cancel_registration', views.ajax_cancel_registration, name='CancelRegistration'),
    path('delete_account', views.ajax_delete_account, name='DeleteAccount'),
]
