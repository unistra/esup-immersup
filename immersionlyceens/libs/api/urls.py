"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('batch_cancel_registration', views.ajax_batch_cancel_registration, name='BatchCancelRegistration'),
    path('cancel_alert', views.ajax_cancel_alert, name='cancel_alert'),
    path('cancel_registration', views.ajax_cancel_registration, name='CancelRegistration'),
    path(
        'check_course_publication/<int:course_id>', views.ajax_check_course_publication, name='checkCoursePublication',
    ),
    path('check_vacations', views.ajax_check_date_between_vacation, name='CheckVacations'),
    path('delete_account', views.ajax_delete_account, name='DeleteAccount'),
    path('delete_course', views.ajax_delete_course, name='DeleteCourses'),
    path('get_agreed_highschools', views.ajax_get_agreed_highschools, name='GetAgreedHighSchools'),
    path('get_immersions_proposal_establishments', views.ajax_get_immersions_proposal_establishments, name='GetImmersionsProposalEstablishments'),
    path('get_alerts', views.ajax_get_alerts, name='get_alerts'),
    path('get_available_documents/', views.ajax_get_documents, name='get_available_documents'),
    path('get_available_students/<int:slot_id>', views.ajax_get_available_students, name='getAvailableStudents'),
    path('get_available_vars/<int:template_id>', views.ajax_get_available_vars, name='GetAvailableVars',),
    path('get_buildings/<int:campus_id>', views.ajax_get_buildings, name='get_buildings',),
    path('get_course_speakers/<int:course_id>', views.ajax_get_course_speakers, name='get_course_speakers',),
    path('get_visit_speakers/<int:visit_id>', views.ajax_get_visit_speakers, name='get_visit_speakers',),
    path('get_event_speakers/<int:event_id>', views.ajax_get_event_speakers, name='get_event_speakers',),
    path(
        'get_courses_by_training/<int:structure_id>/<int:training_id>',
        views.ajax_get_courses_by_training,
        name='get_courses_training',
    ),
    path('get_courses_by_training/<int:training_id>', views.ajax_get_courses_by_training, name='get_courses_training',),
    path('get_courses/', views.ajax_get_courses, name='GetCourses'),
    path('get_csv_anonymous/', views.get_csv_anonymous, name='get_csv_anonymous'),
    path('get_csv_highschool/', views.get_csv_highschool, name='get_csv_highschool'),
    path('get_csv_structures/', views.get_csv_structures, name='get_csv_structures'),
    path('get_duplicates', views.ajax_get_duplicates, name='get_duplicates'),
    path('get_highschool_students/', views.ajax_get_highschool_students, name='get_highschool_students'),
    path('get_highschool_students/no_record', views.ajax_get_highschool_students, name='get_students_without_record'),
    path('get_immersions/<int:user_id>', views.ajax_get_immersions, name='get_immersions',),

    path('get_other_registrants/<int:immersion_id>', views.ajax_get_other_registrants, name='get_other_registrants',),
    path('get_person', views.ajax_get_person, name='PersonByName'),
    path('get_slot_registrations/<int:slot_id>', views.ajax_get_slot_registrations, name='get_slot_registrations',),
    path('slots', views.slots, name='slots_list',),
    path('get_student_records/', views.ajax_get_student_records, name='GetStudentRecords'),
    path('get_students_presence', views.ajax_get_student_presence, name='ajax_get_student_presence'),
    path(
        'get_students_presence/<date_from>/<date_until>',
        views.ajax_get_student_presence,
        name='ajax_get_student_presence_dates',
    ),
    path('get_trainings', views.ajax_get_trainings, name='GetTrainings'),

    path("trainings/highschool/", views.TrainingHighSchoolList.as_view(), name="get_trainings_highschool"),
    path("trainings/highschool/<int:pk>", views.TrainingHighSchoolList.as_view(), name="get_training_highschool"),
    path("training/<int:pk>", views.TrainingView.as_view(), name="training_api"),

    path('keep_entries', views.ajax_keep_entries, name='keep_entries'),
    path('register', views.ajax_slot_registration, name='SlotRegistration'),
    path('reject_student/', views.ajax_reject_student, name='rejectStudent'),
    path('send_email_contact_us', views.ajax_send_email_contact_us, name='SendEmailContactUs'),
    path('send_email', views.ajax_send_email, name='SendEmail'),
    path('set_attendance', views.ajax_set_attendance, name='SetAttendance'),
    path('set_course_alert', views.ajax_set_course_alert, name='set_course_alert'),
    path('validate_student/', views.ajax_validate_student, name='validateStudent'),

    path('get_highschool_speakers/<int:highschool_id>', views.ajax_get_highschool_speakers, name='get_highschool_speakers'),

    path('remove_link', views.remove_link, name='remove_link'),

    # DRF
    path('campuses/', views.CampusList.as_view(), name='campus_list'),
    path('establishments/', views.EstablishmentList.as_view(), name='establishment_list'),
    path('establishment/<int:id>', views.GetEstablishment.as_view(), name='establishment_list'),

    path('structures/', views.StructureList.as_view(), name='structure_list'),
    path('buildings/', views.BuildingList.as_view(), name='building_list'),
    path('trainingdomains/', views.TrainingDomainList.as_view(), name='training_domain_list'),
    path('trainingsubdomains/', views.TrainingSubdomainList.as_view(), name='training_subdomain_list'),
    path('trainings/', views.TrainingList.as_view(), name='training_list'),
    path('courses/', views.CourseList.as_view(), name='course_list'),

    path('visits/', views.VisitList.as_view(), name='visit_list'),
    path('visit/<int:pk>', views.VisitDetail.as_view(), name='visit_detail'),

    path('off_offer_events/', views.OffOfferEventList.as_view(), name='off_offer_event_list'),
    path('off_offer_event/<int:pk>', views.OffOfferEventDetail.as_view(), name='off_offer_event_detail'),

    path('high_school_levels', views.HighSchoolLevelList.as_view(), name='high_school_level_list'),
    path('high_school_level/<int:pk>', views.HighSchoolLevelDetail.as_view(), name='high_school_level_detail'),

    path('visitor/records/<operator>', views.VisitorRecordValidation.as_view(), name="visitors_records"),

    path('visitor/record/<record_id>/<operation>', views.VisitorRecordRejectValidate.as_view(), name="validate_reject_visitor"),
    path('sign_charter', views.signCharter, name="sign_charter"),

    path("mailing_list/global", views.MailingListGlobalView.as_view(), name="mailing_list_global"),
    path("mailing_list/structures", views.MailingListStructuresView.as_view(), name="mailing_list_global"),
    path("mailing_list/establishments", views.MailingListEstablishmentsView.as_view(), name="mailing_list_global"),
    path("mailing_list/high_schools", views.MailingListHighSchoolsView.as_view(), name="mailing_list_global"),

    path("mail_template/<int:pk>/preview", views.MailTemplatePreviewAPI.as_view(), name="mail_template_preview"),


    path("commands/annual_purge/", views.AnnualPurgeAPI.as_view(), name="annual_purge"),
]
