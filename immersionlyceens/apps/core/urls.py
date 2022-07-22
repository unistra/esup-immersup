"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    # path('structure', views.structure, name='structure'),
    # path('structure/<structure_code>', views.structure, name='update_structure'),

    path('structure', views.MyStructureView.as_view(), name='structure'),

    path('course', views.course, name='course'),
    path('course/<int:course_id>', views.course, name='modify_course'),
    path('course/<int:course_id>/<int:duplicate>', views.course, name='duplicate_course'),
    path('courses_list', views.courses_list, name='courses_list'),
    path('duplicates', views.duplicated_accounts, name="duplicates"),
    path('high_school/<int:high_school_id>', views.my_high_school, name='my_high_school'),
    path('high_school_speakers/<int:high_school_id>', views.my_high_school_speakers, name='my_high_school_speakers'),
    path(
        'hs_record_manager/<int:hs_record_id>', views.highschool_student_record_form_manager, name='hs_record_manager'
    ),
    path('my_students', views.MyStudents.as_view(), name='my_students'),
    path('mycourses/', views.mycourses, name='mycourses'),
    path('myvisits/', views.myvisits, name='myvisits'),
    path('myevents/', views.myevents, name='myevents'),
    path('myslots/<str:slots_type>', views.myslots, name='myslots'),
    path('slots/', views.CourseSlotList.as_view(), name='courses_slots'),
    path('slots/<int:highschool_id>/<int:training_id>/<int:course_id>', views.CourseSlotList.as_view(),
         name='high_school_filtered_course_slots_list'),
    path('slots/<int:establishment_id>/<int:structure_id>/<int:training_id>/<int:course_id>',
         views.CourseSlotList.as_view(), name='establishment_filtered_course_slots_list'),

    path('slot', views.CourseSlotAdd.as_view(), name='add_course_slot'),
    path('slot/<int:pk>', views.CourseSlotUpdate.as_view(), name='update_course_slot'),
    path('slot/<int:pk>/<int:duplicate>', views.CourseSlotAdd.as_view(), name='duplicate_course_slot'),
    path('slot/add/<int:highschool_id>/<int:training_id>/<int:course_id>', views.CourseSlotAdd.as_view(),
         name='add_high_school_course_slot'),
    path('slot/add/<int:establishment_id>/<int:structure_id>/<int:training_id>/<int:course_id>',
         views.CourseSlotAdd.as_view(), name='add_establishment_course_slot'),
    path('slot/delete/<int:slot_id>', views.del_slot, name='delete_slot'),

    path('stats/', views.stats, name="stats"),
    path('visitor_validation/', views.VisitorValidationView.as_view(), name="visitor_validation"),
    path('student_validation/', views.student_validation, name='student_validation_global'),
    path('student_validation/<int:high_school_id>/', views.student_validation, name='student_validation'),
    path('students_presence', views.students_presence, name="students_presence"),
    path('speaker', views.speaker, name='speaker'),
    path('speaker/<int:id>', views.speaker, name='edit_speaker'),

    path("training", views.TrainingList.as_view(), name="trainings"),
    path("training/add", views.TrainingAdd.as_view(), name="training_add"),
    path("training/<int:pk>/update", views.TrainingUpdate.as_view(), name="training_update"),

    path("visits", views.VisitList.as_view(), name="visits"),
    path("visit/add", views.VisitAdd.as_view(), name="add_visit"),
    path("visit/<int:pk>", views.VisitUpdate.as_view(), name="update_visit"),
    path('visit/<int:pk>/<int:duplicate>', views.VisitAdd.as_view(), name='duplicate_visit'),

    path('visits_slots/', views.VisitSlotList.as_view(), name='visits_slots'),
    path('visits_slots/<int:establishment_id>/<str:structure_id>/<int:highschool_id>/<int:visit_id>',
         views.VisitSlotList.as_view(), name='establishment_filtered_visits_slots_list'),

    path('visit_slot', views.VisitSlotAdd.as_view(), name='add_visit_slot'),
    path('visit_slot/<int:pk>', views.VisitSlotUpdate.as_view(), name='update_visit_slot'),
    path('visit_slot/<int:pk>/<int:duplicate>', views.VisitSlotAdd.as_view(), name='duplicate_visit_slot'),
    path('visit_slot/add/<int:establishment_id>/<str:structure_id>/<int:highschool_id>/<int:visit_id>',
         views.VisitSlotAdd.as_view(), name='add_establishment_visit_slot'),

    path("off_offer_events", views.OffOfferEventsList.as_view(), name="off_offer_events"),
    path("off_offer_event/add", views.OffOfferEventAdd.as_view(), name="add_off_offer_event"),
    path("off_offer_event/<int:pk>", views.OffOfferEventUpdate.as_view(), name="update_off_offer_event"),
    path('off_offer_event/<int:pk>/<int:duplicate>', views.OffOfferEventAdd.as_view(), name='duplicate_off_offer_event'),

    path('off_offer_events_slots/', views.OffOfferEventSlotList.as_view(), name='off_offer_events_slots'),
    path('off_offer_events_slots/<int:highschool_id>/<int:event_id>', views.OffOfferEventSlotList.as_view(),
         name='high_school_filtered_events_slots_list'),
    path('off_offer_events_slots/<int:establishment_id>/<str:structure_id>/<int:event_id>',
         views.OffOfferEventSlotList.as_view(),
         name='establishment_filtered_events_slots_list'),

    path('off_offer_event_slot', views.OffOfferEventSlotAdd.as_view(), name='add_off_offer_event_slot'),
    path('off_offer_event_slot/<int:pk>', views.OffOfferEventSlotUpdate.as_view(), name='update_ff_offer_event_slot'),
    path('off_offer_event_slot/<int:pk>/<int:duplicate>', views.OffOfferEventSlotAdd.as_view(),
         name='duplicate_off_offer_event_slot'),

    path('off_offer_event_slot/add/<int:highschool_id>/<int:event_id>', views.OffOfferEventSlotAdd.as_view(),
         name='add_high_school_event_slot'),
    path('off_offer_event_slot/add/<int:establishment_id>/<str:structure_id>/<int:event_id>',
         views.OffOfferEventSlotAdd.as_view(), name='add_establishment_event_slot'),
    path('charter', views.charter, name='charter')
]
