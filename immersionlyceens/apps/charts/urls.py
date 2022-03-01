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
    path('highschool_trainings_charts', views.highschool_trainings_charts, name='highschool_trainings_charts'),
    path('global_trainings_charts', views.global_trainings_charts, name='global_trainings_charts'),
    path('highschool_global_trainings_charts', views.global_trainings_charts, {'my_trainings': True },
         name='highschool_global_trainings_charts'),
    path('establishment_trainings_charts', views.global_trainings_charts, {'my_trainings': True },
         name='establishment_trainings_charts'),
    path('global_registrations_charts', views.global_registrations_charts, name='global_registrations_charts'),
    path('global_slots_charts', views.global_slots_charts, name='global_slots_charts'),

    # API part
    # TODO : update paths to have more REST compliant urls
    path('get_highschool_charts/<int:highschool_id>', api.highschool_charts, name='get_highschool_charts'),
    path('get_highschool_domains_charts/<int:highschool_id>/<int:level>', api.highschool_domains_charts, name='get_highschool_domains_charts'),
    path('get_global_domains_charts', api.global_domains_charts, name='get_global_domains_charts'),
    path('get_charts_filters_data', api.get_charts_filters_data, name='get_charts_filters_data'),
    path('get_highschool_trainings_charts', api.get_highschool_trainings_charts, name='get_highschool_trainings_charts'),
    path('get_global_trainings_charts', api.get_global_trainings_charts, name='get_global_trainings_charts'),
    path('get_registration_charts', api.get_registration_charts, name='get_registration_charts'),
    path('get_registration_charts_cats', api.get_registration_charts_cats, name='get_registration_charts_cats'),
    path('get_slots_charts', api.get_slots_charts, name='get_slots_charts'),
    path('get_slots_data', api.get_slots_data, name='get_slots_data'),
    path('get_slots_data/csv', api.get_slots_data, {'csv_mode': True }, name='get_slots_csv_data'),
]