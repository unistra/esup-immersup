# -*- coding: utf-8 -*-

"""
Url configuration for the Immersion application API
"""

from django.urls import path
from . import views

app_name = 'immersion'

urlpatterns = [
    path('', views.home, name='home'),
    #
    # path('login', views.CustomLogin.as_view(), name='login'),
    path('login', views.customLogin, name='login'),
    path('register', views.register, name='register'),
    path('recovery', views.recovery, name='recovery'),
    path('activate/<hash>', views.activate, name='activate'),
    path('record', views.student_record, name='record'),
    path('record/<int:record_id>', views.student_record, name='modify_record'),
    path('resend_activation', views.resend_activation, name='resend_activation'),
]
