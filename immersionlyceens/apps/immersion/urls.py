# -*- coding: utf-8 -*-

"""
Url configuration for the Immersion application API
"""

from django.urls import path

from . import views

app_name = 'immersion'

urlpatterns = [
    path('', views.home, name='home'),
    path('login', views.login, name='login'),
    path('register', views.register, name='register'),
    path('recovery', views.recovery, name='recovery'),
    path('activate/<hash>', views.activate, name='activate'),
]
