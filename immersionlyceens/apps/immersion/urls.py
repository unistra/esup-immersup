"""
Url configuration for the Immersion application API
"""

from django.urls import path

from . import views

app_name = 'immersion'

urlpatterns = [
    path('', views.home, name='home'),
    # path('activate/<hash>', views.activate, name='activate'),
    path('activate/<hash>', views.ActivateView.as_view(), name='activate'),
    path('dl/attestation/<int:immersion_id>', views.immersion_attestation_download, name='attestation_download'),
    path('change_password', views.change_password, name='change_password'),
    path('hs_record', views.high_school_student_record, name='hs_record'),
    path('hs_record/<int:record_id>', views.high_school_student_record, name='modify_hs_record'),

    path('visitor_record', views.VisitorRecordView.as_view(), name="visitor_record"),
    path('visitor_record/<int:record_id>', views.VisitorRecordView.as_view(), name="visitor_record_by_id"),

    path('registrations', views.registrations, name='registrations'),

    # path('login', views.customLogin, name='login'),
    # path('login/<profile>', views.customLogin, name='login'),

    path("login", views.CustomLoginView.as_view(), name="login"),
    path("login/<profile>", views.CustomLoginView.as_view(), name="login"),

    # path('recovery', views.recovery, name='recovery'),

    path('recovery', views.RecoveryView.as_view(), name='recovery'),


    path('register', views.register, name='register'),

    path('resend_activation', views.resend_activation, name='resend_activation'),

    path('reset_password/<hash>', views.reset_password, name='reset_password'),
    path('student_record', views.student_record, name='student_record'),
    path('student_record/<int:record_id>', views.student_record, name='modify_student_record'),
]
