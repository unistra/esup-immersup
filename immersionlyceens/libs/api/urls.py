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
    path('get_available_documents/', views.ajax_get_documents, name='get_available_documents'),
    path('get_available_vars/<int:template_id>', views.ajax_get_available_vars, name='GetAvailableVars',),
    path('get_buildings/<int:campus_id>', views.ajax_get_buildings, name='get_buildings',),
    path('get_courses/<int:component_id>/', views.ajax_get_courses, name='GetCourses'),
    path('get_courses_by_training/<int:training_id>', views.ajax_get_courses_by_training, name='get_courses_training',),
    path('get_course_teachers/<int:course_id>', views.ajax_get_course_teachers, name='get_course_teachers',),
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
    path('get_slots', views.ajax_get_slots, name='get_slots',),
    path('get_students', views.ajax_get_students, name='getStudents'),
    path('get_students_presence', views.ajax_get_student_presence, name='ajax_get_student_presence'),
    path('get_students_presence/<date_from>/<date_until>', views.ajax_get_student_presence, name='ajax_get_student_presence_dates'),
    path('get_highschool_students/no_record', views.ajax_get_highschool_students, name='get_students_without_record'),
    path('get_highschool_students/<int:highschool_id>/',
        views.ajax_get_highschool_students,
        name='get_highschool_students',
    ),
    path('get_highschool_students/', views.ajax_get_highschool_students, name='get_all_students'),
    path('get_student_records/', views.ajax_get_student_records, name='GetStudentRecords'),
    path('get_slots_by_course/<int:course_id>', views.ajax_get_slots_by_course, name='get_slots_by_course',),
    path('get_trainings', views.ajax_get_trainings, name='GetTrainings'),
    path('get_immersions/<int:user_id>/<immersion_type>', views.ajax_get_immersions, name='get_immersions',),
    path('get_immersions/<int:user_id>', views.ajax_get_immersions, name='get_immersions',),
    path('get_other_registrants/<int:immersion_id>', views.ajax_get_other_registrants, name='get_other_registrants',),
    path('get_slot_registrations/<int:slot_id>', views.ajax_get_slot_registrations, name='get_slot_registrations',),
    # VALIDATE / REJECT ACTION
    path('reject_student/', views.ajax_reject_student, name='rejectStudent'),
    path('validate_student/', views.ajax_validate_student, name='validateStudent'),
    path(
        'check_course_publication/<int:course_id>', views.ajax_check_course_publication, name='checkCoursePublication',
    ),
    path('register', views.ajax_slot_registration, name='SlotRegistration'),
    path('cancel_registration', views.ajax_cancel_registration, name='CancelRegistration'),
    path('batch_cancel_registration', views.ajax_batch_cancel_registration, name='BatchCancelRegistration'),
    path('set_attendance', views.ajax_set_attendance, name='SetAttendance'),
    path('delete_account', views.ajax_delete_account, name='DeleteAccount'),
    path('send_email', views.ajax_send_email, name='SendEmail'),
    path('get_csv_components/<int:component_id>', views.get_csv_components, name='get_csv_components'),
    path('get_csv_highschool/<int:high_school_id>', views.get_csv_highschool, name='get_csv_highschool'),
    path('get_csv_anonymous_immersion/', views.get_csv_anonymous_immersion, name='get_csv_anonymous_immersion'),
    path('send_email_contact_us', views.ajax_send_email_contact_us, name='SendEmailContactUs'),
    path('set_course_alert', views.ajax_set_course_alert, name='set_course_alert'),
    path('get_alerts', views.ajax_get_alerts, name='get_alerts'),
    path('cancel_alert', views.ajax_cancel_alert, name='cancel_alert'),
    path('get_duplicates', views.ajax_get_duplicates, name='get_duplicates'),
    path('keep_entries', views.ajax_keep_entries, name='keep_entries')
]
