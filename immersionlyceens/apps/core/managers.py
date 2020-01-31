from django.db import models

class ActiveManager(models.Manager):
    """
    Get active objects
    """

    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class ComponentQuerySet(models.QuerySet):
    """
    """
    def user_cmps(self, user, *groups):
        cmp_filter = {'referents': user}
        # Check if the user is in a group authorized to manage all the components
        if user.has_groups(*groups):
            cmp_filter = {}

        return self.filter(**cmp_filter)