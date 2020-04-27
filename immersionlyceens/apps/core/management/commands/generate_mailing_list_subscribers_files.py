#!/usr/bin/env python
"""
Generate files containing mailing-lists subscribers
- one file for the global mailing-list (every student registered to a slot)
- one file for each component (every student registered to at list one slot under the component)
"""
import datetime
import logging
import sys
from os import W_OK, access, mkdir, path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import Component, Immersion, ImmersionUser, Slot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        all_filename = None
        output_dir = settings.MAILING_LIST_FILES_DIR

        if not path.exists(output_dir):
            try:
                mkdir(output_dir, mode=0o700)
            except Exception as e:
                logger.error("Cannot create output directory %s : %s", output_dir, e)
                return
        elif not path.isdir(output_dir):
            logger.error("'%s' exists but is not a directory", output_dir)
            return
        elif not access(output_dir, W_OK):
            logger.error("'%s' exists but is not writable", output_dir)
            return

        try:
            all_filename = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            logger.error("'GLOBAL_MAILING_LIST' setting does not exist (check admin GeneralSettings values)", output_dir)
            sys.exit("GLOBAL_MAILING_LIST variable not configured properly in core General Settings")

        # Global mailing list file : all students
        if all_filename:
            output_file = path.join(settings.MAILING_LIST_FILES_DIR, all_filename)
            try:
                with open(output_file, "w") as all_registered_fd:
                    all_registered_fd.write('\n'.join([email for email in
                        ImmersionUser.objects.filter(Q(student_record__isnull=False)|Q(high_school_student_record__isnull=False))\
                        .values_list('email', flat=True).distinct()]))
            except Exception as e:
                logger.error("Cannot write mailing list file %s : %s", all_filename, e)

        # Components mailing list files
        for component in Component.objects.filter(mailing_list__isnull=False):
            output_file = path.join(settings.MAILING_LIST_FILES_DIR, component.mailing_list)
            try:
                with open(output_file, "w") as component_fd:
                    component_fd.write('\n'.join(
                        [email for email in Immersion.objects.filter(
                            cancellation_type__isnull=True, slot__course__component=component) \
                                  .values_list('student__email', flat=True).distinct()])
                    )
            except Exception as e:
                logger.error("Cannot write mailing list file %s : %s", component.mailing_list, e)
