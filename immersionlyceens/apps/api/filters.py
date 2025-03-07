"""API specific filters"""
import django_filters

from immersionlyceens.apps.core import models

class ImmersionUserFilter(django_filters.FilterSet):
    postbac_immersion = django_filters.BooleanFilter(
        field_name='highschool__postbac_immersion',
    )

    group = django_filters.CharFilter(
        field_name='groups__name',
    )

    class Meta:
        model = models.ImmersionUser
        fields = ["postbac_immersion", "group"]
