"""
Url configuration for the core application API
"""

from django.urls import path

from . import views

urlpatterns = [
    path('departments', views.ajax_get_departments, name='ajax_get_departments'),
    path('cities/<int:dep>', views.ajax_get_cities, name='ajax_get_cities'),
    path('zipcodes/<int:dep>/<str:city>',views.ajax_get_zipcodes, name='ajax_get_zipcodes'),
]
