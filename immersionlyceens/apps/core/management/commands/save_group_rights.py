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
        perms = defaultdict(list)
        for group in Group.objects.all().order_by('name'):
            perms[group.name] = [permission.codename for permission in group.permissions.all().order_by('codename')]

        with open(normpath(join(settings.SITE_ROOT, "group_permissions_codenames.json")), "w+") as fp:
            fp.write(json.dumps(perms))
