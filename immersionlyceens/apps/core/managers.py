import datetime

from django.db import models
from django.db.models import Q


class ActiveManager(models.Manager):
    """
    Get active objects
    """

    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class ComponentQuerySet(models.QuerySet):
    """
    """

    def user_strs(self, user, *groups):
        cmp_filter = {'referents': user}
        # Check if the user is in a group authorized to manage all structures
        if user.has_groups(*groups):
            cmp_filter = {}

        return self.filter(**cmp_filter)


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
