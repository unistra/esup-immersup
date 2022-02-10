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
    path('structure_trainings_charts', views.structure_trainings_charts, name='structure_trainings_charts'),
    path('global_registrations_charts', views.global_registrations_charts, name='global_registrations_charts'),
    path('global_slots_charts', views.global_slots_charts, name='global_slots_charts'),

    # API part
    path('get_highschool_charts/<highschool_id>', api.highschool_charts, name='get_highschool_charts'),
    path('get_highschool_domains_charts/<highschool_id>/<int:level>', api.highschool_domains_charts, name='get_highschool_domains_charts'),
    path('get_global_domains_charts', api.global_domains_charts, name='get_global_domains_charts'),
    path('get_charts_filters_data', api.get_charts_filters_data, name='get_charts_filters_data'),
    path('get_trainings_charts', api.get_trainings_charts, name='get_trainings_charts'),
    path('get_structure_trainings_charts', api.get_structure_trainings_charts, name='get_structure_trainings_charts'),
    path('get_registration_charts/<int:level_value>', api.get_registration_charts, name='get_registration_charts'),
    path('get_registration_charts_cats', api.get_registration_charts_cats, name='get_registration_charts_cats'),
    path('get_slots_charts', api.get_slots_charts, name='get_slots_charts'),
    path('get_slots_data', api.get_slots_data, name='get_slots_data'),
    path('get_slots_data/csv', api.get_slots_data, {'csv_mode': True }, name='get_slots_csv_data'),
]