"""
Url configuration for the geoapi API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('cities/<str:dep>', views.ajax_get_cities, name='ajax_get_cities'),
    path('departments', views.ajax_get_departments, name='ajax_get_departments'),
    path('zipcodes/<str:dep>/<str:city>', views.ajax_get_zipcodes, name='ajax_get_zipcodes'),
]
