#!/usr/bin/env python
"""
Send pending highschool students accounts validations notifications to high school referents
"""
import logging

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _
from ...models import HighSchool, ImmersionUser
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord, VisitorRecord
from . import Schedulable

logger = logging.getLogger(__name__)

class Command(BaseCommand, Schedulable):
    """
    """

    def handle(self, *args, **options):
        success = "%s : %s" % (_("Send pending validations notification"), _("success"))
        returns = []

        hs_to_validate = HighSchoolStudentRecord.STATUSES["TO_VALIDATE"]
        hs_to_revalidate = HighSchoolStudentRecord.STATUSES["TO_REVALIDATE"]

        visitors_to_validate = VisitorRecord.STATUSES["TO_VALIDATE"]
        visitors_to_revalidate = VisitorRecord.STATUSES["TO_VALIDATE"]

        # High schools with conventions
        highschools = HighSchool.objects.filter(
            with_convention=True,
            student_records__validation__in=[hs_to_validate, hs_to_revalidate]
        ).distinct()

        for highschool in highschools:
            referents = highschool.users.prefetch_related("groups").filter(groups__name='REF-LYC')

            for referent in referents:
                msg = referent.send_message(None, 'CPT_AVALIDER_LYCEE')
                if msg:
                    returns.append(msg)


        # Visitors and high school without conventions : send reminders to establishments managers
        hs_records = HighSchoolStudentRecord.objects\
            .prefetch_related("highschool")\
            .filter(
                highschool__with_convention=False,
                validation__in=[hs_to_validate, hs_to_revalidate]
            )\
            .exists()

        visitor_records = VisitorRecord.objects\
            .filter(
                validation__in=[visitors_to_validate, visitors_to_revalidate]
            )\
            .exists()

        if hs_records or visitor_records:
            manager_groups = ["REF-ETAB-MAITRE", "REF-ETAB"]
            for user in ImmersionUser.objects.prefetch_related("groups").filter(groups__name__in=manager_groups):
                msg = user.send_message(None, 'CPT_AVALIDER_REF_ETAB')
                if msg:
                    returns.append(msg)

        if returns:
            for line in returns:
                logger.error(line)

            return "\n".join(returns)


        logger.info(success)
        return success