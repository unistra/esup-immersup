import datetime

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.apps import apps


class ActiveManager(models.Manager):
    """
    Get active objects
    """

    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class EstablishmentQuerySet(models.QuerySet):
    def user_establishments(self, user):
        if user.is_master_establishment_manager() or user.is_operator():
            return self
        elif (user.is_establishment_manager() or user.is_structure_manager()) and user.establishment:
            return self.filter(pk=user.establishment.id)

        return self.none()

class StructureQuerySet(models.QuerySet):
    """
    """

    def user_strs(self, user, *groups):
        str_filter = {'referents': user}
        # Check if the user is in a group authorized to manage all structures
        if user.has_groups(*groups):
            str_filter = {}

        return self.filter(**str_filter)


class HighSchoolAgreedManager(models.Manager):
    """
    Return all the 'valid' high schools:
    - active = True
    - conventions depending on General Settings
    - with allow
    """
    def get_queryset(self):
        general_settings_class = apps.get_model('core', 'GeneralSettings')

        # Convention General Settings
        today = timezone.localdate()

        try:
            w_convention = general_settings_class.objects.get(setting="ACTIVATE_HIGH_SCHOOL_WITH_AGREEMENT")
            hs_w_convention = w_convention.parameters.get("value", True)
        except general_settings_class.DoesNotExist:
            hs_w_convention = True

        try:
            wo_convention = general_settings_class.objects.get(setting="ACTIVATE_HIGH_SCHOOL_WITHOUT_AGREEMENT")
            hs_wo_convention = wo_convention.parameters.get("value", False)
        except general_settings_class.DoesNotExist:
            hs_wo_convention = False

        highschool_filters = {'active': True, }

        date_filters = {
            'convention_start_date__lte': today,
            'convention_end_date__gte': today,
        }

        base_queryset = super().get_queryset()

        # One is True, but not the other
        if hs_w_convention != hs_wo_convention:
            highschool_filters["with_convention"] = hs_w_convention

            if hs_w_convention:
                highschool_filters.update(date_filters)

            return base_queryset.filter(**highschool_filters)

        # The only alternative is that both settings are True, it's a bit more tricky
        return base_queryset.filter(
            Q(with_convention=False)|Q(**date_filters), **highschool_filters
        )

class CustomDeleteManager(models.Manager):
    def delete(self):
        for obj in self.get_queryset():
            obj.delete()


class PostBacImmersionManager(models.Manager):
    """
    Get high schools offering immersions
    """

    def get_queryset(self):
        return super().get_queryset().filter(postbac_immersion=True)
