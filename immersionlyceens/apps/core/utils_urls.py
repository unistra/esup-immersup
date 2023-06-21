"""
Url configuration for the core utils
"""

from django.urls import path

from . import utils

urlpatterns = [
    path('slots', utils.slots, name='get_slots'),
    path('set_session_values', utils.set_session_values, name='set_session_values')
]