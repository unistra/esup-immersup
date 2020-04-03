# -*- coding: utf-8 -*-

"""
Url configuration for the charts application API
"""

from django.urls import path
from . import views, api

app_name = 'charts'

urlpatterns = [
    path('highschool_charts', views.highschool_charts, name='highschool_charts'),
    # path('get_highschool_charts/<highschool_id>', api.HighSchoolChartsView.as_view(), name='get_highschool_charts'),
    path('get_highschool_charts/<highschool_id>', api.highschool_charts, name='get_highschool_charts'),
]