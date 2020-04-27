#!/usr/bin/env python
"""
Update annual statistics data
"""
import datetime
import logging
import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, Q, Sum
from django.utils.translation import ugettext_lazy as _

from ...models import (
    AnnualStatistics, Component, Course, HighSchool, Immersion, ImmersionUser, Slot, Training, UniversityYear,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        try:
            year = UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            logger.error(_("No active year found, can't update statistics"))
            sys.exit()

        try:
            annual_stats = AnnualStatistics.objects.get(year=year.label)
        except AnnualStatistics.DoesNotExist:
            annual_stats = AnnualStatistics.objects.create(year=year.label)

        hs_queryset = HighSchool.objects.filter(
            convention_start_date__isnull=False, convention_end_date__isnull=False)

        # Approved high schools
        annual_stats.approved_highschools = hs_queryset.count()

        # Approved high schools with no registered students
        annual_stats.highschools_without_students = hs_queryset.filter(student_records__isnull=True).count()

        # Total number of registered students
        annual_stats.platform_registrations = ImmersionUser.objects.filter(
            Q(student_record__isnull=False)|Q(high_school_student_record__validation=2)
        ).count()

        # Number of registered students to at least one immersion
        annual_stats.one_immersion_registrations = ImmersionUser.objects.filter(
            immersions__isnull=False, immersions__cancellation_type__isnull=True
        ).distinct().count()

        # Number of registered students to more than one immersion
        annual_stats.multiple_immersions_registrations = ImmersionUser.objects.annotate(
            imm_count=Count('immersions', filter=Q(immersions__cancellation_type__isnull=True))).filter(
            imm_count__gt=1).count()

        # Number of participants in at least one immersion
        annual_stats.participants_one_immersion = ImmersionUser.objects.filter(
            immersions__attendance_status=1
        ).distinct().count()

        # Number of participants in more than one immersion
        annual_stats.multiple_immersions_registrations = ImmersionUser.objects.annotate(
            imm_count=Count('immersions', filter=Q(immersions__attendance_status=1))).filter(
            imm_count__gt=1).count()

        # Number of immersions registrations
        annual_stats.immersion_registrations = Immersion.objects.filter(
            cancellation_type__isnull=True
        ).count()

        # Number of offered seats
        annual_stats.seats_count = Slot.objects.filter(published=True).aggregate(
            seats_count=Sum('n_places'))['seats_count']

        # Participating components
        annual_stats.components_count = Component.objects.annotate(
            slot_nb=Count('courses__slots', filter=Q(courses__slots__published=True)))\
            .filter(slot_nb__gt=0).count()

        # Trainings with at least one slot
        annual_stats.trainings_one_slot_count = Training.objects.annotate(
            slot_nb=Count('courses__slots', filter=Q(courses__slots__published=True)))\
            .filter(slot_nb__gt=0).count()

        # Courses with at least one slot
        annual_stats.courses_one_slot_count = Course.objects.annotate(
            slot_nb=Count('slots', filter=Q(slots__published=True))) \
            .filter(slot_nb__gt=0).count()

        annual_stats.total_slots_count = Slot.objects.filter(published=True).count()

        annual_stats.save()
