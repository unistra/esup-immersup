"""
Urls for the UAI API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('establishments/<str:value>', views.ajax_get_establishments, name='get_establishments'),
]
