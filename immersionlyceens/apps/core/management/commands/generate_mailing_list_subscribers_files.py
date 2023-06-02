#!/usr/bin/env python
"""
Generate files containing mailing-lists subscribers
- one file for the global mailing-list (every student registered to a slot)
- one file for each structure (every student registered to at list one slot under the structure)
"""
import datetime
import logging
import sys
from os import W_OK, access, mkdir, path
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

from ...models import Structure, Immersion, ImmersionUser, Slot, Establishment, HighSchool
from . import Schedulable

logger = logging.getLogger(__name__)


class Command(BaseCommand, Schedulable):
    """
    """

    @staticmethod
    def write_mailing_list(output_file: str, emails: List[str], mailing_list: str):
        try:
            with open(output_file, "w") as structure_fd:
                structure_fd.write('\n'.join(emails))
        except Exception as e:
            logger.error("Cannot write mailing list file %s : %s", mailing_list, e)

    def handle(self, *args, **options):
        success = _("Generate mailing list subscriber files : success")
        all_filename = None
        output_dir = settings.MAILING_LIST_FILES_DIR
        returns = []
        msg = ""

        if not path.exists(output_dir):
            try:
                mkdir(output_dir, mode=0o700)
            except Exception as e:
                msg = _("Cannot create output directory %s : %s") % (output_dir, e)
        elif not path.isdir(output_dir):
            msg = _("'%s' exists but is not a directory") % output_dir
        elif not access(output_dir, W_OK):
            msg = _("'%s' exists but is not writable") % output_dir

        # Exit
        if msg:
            logger.error(msg)
            raise CommandError(msg)

        try:
            all_filename = get_general_setting('GLOBAL_MAILING_LIST')
        except (ValueError, NameError):
            msg = _("'GLOBAL_MAILING_LIST' setting does not exist (check admin GeneralSettings values)") % output_dir
            logger.error(msg)
            raise CommandError(msg)

        # Global mailing list file : all students, hs students and visitors
        if all_filename:
            output_file = path.join(settings.MAILING_LIST_FILES_DIR, f"structure_{all_filename}")
            try:
                with open(output_file, "w") as all_registered_fd:
                    all_registered_fd.write('\n'.join([email for email in ImmersionUser.objects.filter(
                        Q(student_record__isnull=False)
                      | Q(high_school_student_record__validation=2, high_school_student_record__isnull=False) \
                      | Q(visitor_record__validation=2, visitor_record__isnull=False) \
                        ) \
                        .values_list('email', flat=True) \
                        .distinct()]
                    ))
            except Exception as e:
                returns.append(_("Cannot write mailing list file %s : %s") % (all_filename, e))

        # Structures mailing list files
        for structure in Structure.objects.filter(mailing_list__isnull=False):
            output_file = path.join(settings.MAILING_LIST_FILES_DIR, structure.mailing_list)
            try:
                with open(output_file, "w") as structure_fd:
                    structure_fd.write('\n'.join(
                        [email for email in Immersion.objects.filter(
                            cancellation_type__isnull=True, slot__course__structure=structure) \
                            .values_list('student__email', flat=True).distinct()])
                    )
            except Exception as e:
                returns.append(_("Cannot write mailing list file %s : %s") % (structure.mailing_list, e))

        # Establishment mailing list files
        for establishment in Establishment.objects.filter(mailing_list__isnull=False):
            mailing_list = [email for email in Immersion.objects.filter(cancellation_type__isnull=True).filter(
                Q(slot__course__structure__establishment=establishment) \
                | Q(slot__visit__establishment=establishment) \
                | Q(slot__event__establishment=establishment)
            ).values_list('student__email', flat=True).distinct()]

            output_file = path.join(settings.MAILING_LIST_FILES_DIR, f"establishment_{establishment.mailing_list}")
            self.write_mailing_list(
                output_file=output_file,
                emails=mailing_list,
                mailing_list=establishment.mailing_list
            )

        # High school mailing list files
        for hs in HighSchool.agreed.filter(mailing_list__isnull=False):
            mailing_list = [email for email in Immersion.objects.filter(cancellation_type__isnull=True).filter(
                Q(slot__course__highschool=hs) \
                | Q(slot__visit__highschool=hs) \
                | Q(slot__event__highschool=hs)
            ).values_list('student__email', flat=True).distinct()]

            output_file = path.join(settings.MAILING_LIST_FILES_DIR, f"highschool_{hs.mailing_list}")
            self.write_mailing_list(
                output_file=output_file,
                emails=mailing_list,
                mailing_list=hs.mailing_list
            )

        if returns:
            raise CommandError("\n".join(returns))

        logger.info(success)
        return success