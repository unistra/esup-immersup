# -*- coding: utf-8 -*-

"""
Url configuration for the charts application API
"""

from django.urls import path
from . import views, api

app_name = 'charts'

urlpatterns = [
    path('highschool_charts', views.highschool_charts, name='highschool_charts'),
    path('highschool_domains_charts', views.highschool_domains_charts, name='highschool_domains_charts'),
    path('global_domains_charts', views.global_domains_charts, name='global_domains_charts'),
    path('trainings_charts', views.trainings_charts, name='trainings_charts'),

    # API part
    path('get_highschool_charts/<highschool_id>', api.highschool_charts, name='get_highschool_charts'),
    path('get_highschool_domains_charts/<highschool_id>/<int:level>', api.highschool_domains_charts, name='get_highschool_domains_charts'),
    path('get_global_domains_charts', api.global_domains_charts, name='get_global_domains_charts'),
    path('get_charts_filters_data', api.get_charts_filters_data, name='get_charts_filters_data'),
    path('get_trainings_charts', api.get_trainings_charts, name='get_trainings_charts'),
]