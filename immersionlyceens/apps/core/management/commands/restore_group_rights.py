#!/usr/bin/env python
"""
Dump group rights by codenames
"""
import json
import logging
from os.path import normpath, join
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from django.contrib.auth.models import Group, Permission

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        with open(normpath(join(settings.SITE_ROOT, 'group_permissions_codenames.json')), 'r') as fp:
            j_perms = fp.read()

        perms = json.loads(j_perms)

        for group in Group.objects.all():
            group.permissions.clear()

        for group, permissions in perms.items():
            for codename in permissions:
                try:
                    Group.objects.get(name=group).permissions.add(Permission.objects.get(codename=codename))
                except Group.DoesNotExist:
                    print(f"Group {group} does not exist")
                except Permission.DoesNotExist:
                    print(f"Permission {codename} does not exist")
