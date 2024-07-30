"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('batch_cancel_registration', views.ajax_batch_cancel_registration, name='BatchCancelRegistration'),
    path('groups_batch_cancel_registration', views.ajax_groups_batch_cancel_registration, name='GroupsBatchCancelRegistration'),
    path('cancel_alert', views.ajax_cancel_alert, name='cancel_alert'),
    path('cancel_registration', views.ajax_cancel_registration, name='CancelRegistration'),

    path('validate_slot_date', views.validate_slot_date, name='ValidateSlotDate'),
    path('delete_account', views.ajax_delete_account, name='DeleteAccount'),

    path('get_available_documents/', views.ajax_get_documents, name='get_available_documents'),
    path('get_available_students/<int:slot_id>', views.ajax_get_available_students, name='getAvailableStudents'),
    path('get_available_vars/<int:template_id>', views.ajax_get_available_vars, name='GetAvailableVars',),
    path('get_buildings/<int:campus_id>', views.ajax_get_buildings, name='get_buildings',),

    path('get_csv_anonymous/', views.get_csv_anonymous, name='get_csv_anonymous'),
    path('get_csv_highschool/', views.get_csv_highschool, name='get_csv_highschool'),
    path('get_csv_structures/', views.get_csv_structures, name='get_csv_structures'),
    path('get_duplicates', views.ajax_get_duplicates, name='get_duplicates'),
    path('get_immersions/<int:user_id>', views.ajax_get_immersions, name='get_immersions',),

    path('get_other_registrants/<int:immersion_id>', views.ajax_get_other_registrants, name='get_other_registrants',),
    path('get_person', views.ajax_get_person, name='PersonByName'),
    path('get_slot_registrations/<int:slot_id>', views.ajax_get_slot_registrations, name='get_slot_registrations',),
    path(
        'get_slot_groups_registrations/<int:slot_id>',
        views.ajax_get_slot_groups_registrations,
        name='get_slot_groups_registrations'
    ),
    path('get_student_records/', views.ajax_get_student_records, name='GetStudentRecords'),
    path('get_students_presence', views.ajax_get_student_presence, name='ajax_get_student_presence'),

    #path(
    #    'get_students_presence/<date_from>/<date_until>',
    #    views.ajax_get_student_presence,
    #    name='ajax_get_student_presence_dates',
    #),

    path('keep_entries', views.ajax_keep_entries, name='keep_entries'),
    path('register', views.ajax_slot_registration, name='SlotRegistration'),
    path('group_register', views.ajax_group_slot_registration, name='GroupSlotRegistration'),
    path('reject_student/', views.ajax_reject_student, name='rejectStudent'),
    path('send_email_contact_us', views.ajax_send_email_contact_us, name='SendEmailContactUs'),
    path('send_email', views.ajax_send_email, name='SendEmail'),
    path('set_attendance', views.ajax_set_attendance, name='SetAttendance'),
    path('set_course_alert', views.ajax_set_course_alert, name='set_course_alert'),
    path('validate_student/', views.ajax_validate_student, name='validateStudent'),
    path('remove_link', views.remove_link, name='remove_link'),

    # DRF
    path('campuses', views.CampusList.as_view(), name='campus_list'),
    path('establishments', views.EstablishmentList.as_view(), name='establishment_list'),
    path('establishment/<int:id>', views.GetEstablishment.as_view(), name='establishment_detail'),
    path('structures', views.StructureList.as_view(), name='structure_list'),
    path('buildings', views.BuildingList.as_view(), name='building_list'),
    path('trainingdomains', views.TrainingDomainList.as_view(), name='training_domain_list'),
    path('trainingsubdomains', views.TrainingSubdomainList.as_view(), name='training_subdomain_list'),

    # High schools
    path('highschools', views.HighSchoolList.as_view(), name='highschool_list'),
    path('highschool/<int:pk>', views.HighSchoolDetail.as_view(), name='highschool_detail'),
    path('get_highschool_students', views.ajax_get_highschool_students, name='get_highschool_students'),
    path('get_highschool_students/no_record', views.ajax_get_highschool_students, name='get_students_without_record'),

    # Trainings
    path('trainings', views.TrainingList.as_view(), name='training_list'),
    path("training/<int:pk>", views.TrainingDetail.as_view(), name="training_detail"),

    # Courses
    path('courses', views.CourseList.as_view(), name='course_list'),
    path("course/<int:pk>", views.CourseDetail.as_view(), name="course_detail"),

    path('course_types', views.CourseTypeList.as_view(), name='course_type_list'),
    path("course_type/<int:pk>", views.CourseTypeDetail.as_view(), name="course_type_detail"),

    # The following path may change to 'slots/' in a near future : please always use the 'name'
    path('slots', views.SlotList.as_view(), name='slot_list',),

    # Speakers
    path('speakers', views.SpeakerList.as_view(), name='speaker_list'),
    path('speakers/courses/<int:course_id>', views.SpeakerList.as_view(), name='course_speaker_list'),
    path('speakers/events/<int:event_id>', views.SpeakerList.as_view(), name='event_speaker_list'),

    # Off offer events
    path('off_offer_events', views.OffOfferEventList.as_view(), name='off_offer_event_list'),
    path('off_offer_event/<int:pk>', views.OffOfferEventDetail.as_view(), name='off_offer_event_detail'),

    # High school levels
    path('high_school_levels', views.HighSchoolLevelList.as_view(), name='high_school_level_list'),
    path('high_school_level/<int:pk>', views.HighSchoolLevelDetail.as_view(), name='high_school_level_detail'),

    # Visitor records
    path('visitor/records/<operator>', views.VisitorRecordValidation.as_view(), name="visitors_records"),
    path('visitor/record/<record_id>/<operation>', views.VisitorRecordRejectValidate.as_view(),
         name="validate_reject_visitor"),

    # Immersion periods
    path('periods', views.PeriodList.as_view(), name='period_list'),

    # User course alerts
    path('course_alerts', views.UserCourseAlertList.as_view(), name='user_course_alert_list'),

    # Charter
    path('sign_charter', views.signCharter, name="sign_charter"),

    # Mailing lists
    path("mailing_list/global", views.MailingListGlobalView.as_view(), name="mailing_list_global"),
    path("mailing_list/structures", views.MailingListStructuresView.as_view(), name="mailing_list_global"),
    path("mailing_list/establishments", views.MailingListEstablishmentsView.as_view(), name="mailing_list_global"),
    path("mailing_list/high_schools", views.MailingListHighSchoolsView.as_view(), name="mailing_list_global"),

    # Mail template
    path("mail_template/<int:pk>/preview", views.MailTemplatePreviewAPI.as_view(), name="mail_template_preview"),

    # Annual purge
    path("commands/annual_purge", views.AnnualPurgeAPI.as_view(), name="annual_purge"),

    # Structures Manager notifications settings update
    path("update_structures_notifications", views.ajax_update_structures_notifications, name="update_structures_notifications"),

    # Check if logged user can register a slot
    path('can_register_slot/<int:slot_id>', views.ajax_can_register_slot, name='can_register_slot'),

    # Slots list for search slots page
    path('search_slots_list', views.ajax_search_slots_list, name='search_slots_list'),

    # Slot restrictions
    path('get_slot_restrictions/<int:slot_id>', views.ajax_get_slot_restrictions, name='get_slot_restrictions'),
]
