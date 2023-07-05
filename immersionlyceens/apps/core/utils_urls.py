"""
Url configuration for the core utils
"""

from django.urls import path

from . import utils

urlpatterns = [
    path('slots', utils.slots, name='get_slots'),
    path('set_session_values', utils.set_session_values, name='set_session_values'),
    path('set_training_quota', utils.set_training_quota, name='set_training_quota')
]