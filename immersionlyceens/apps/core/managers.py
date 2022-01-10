import datetime

from django.db import models
from django.db.models import Q


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
    def get_queryset(self):
        """Returns the base QuerySet."""
        return (
            super()
            .get_queryset()
            .exclude(convention_start_date__isnull=True)
            .exclude(convention_start_date__gt=datetime.datetime.now().date())
            .exclude(convention_end_date__lt=datetime.datetime.now().date())
            # .filter(
            #     # Q(convention_end_date__gte=date.today(), convention_start_date__lte=date.today())
            #     Q(convention_start_date__lte=date.today(), convention_end_date__isnull=True,)
            # )
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
