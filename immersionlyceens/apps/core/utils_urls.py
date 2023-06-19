"""
Url configuration for the core utils
"""

from django.urls import path

from . import utils

urlpatterns = [
    path('slots', utils.slots, name='get_slots'),
]