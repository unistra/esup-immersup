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
from django.utils.translation import gettext_lazy as _

from ...models import (
    AnnualStatistics, Structure, Course, HighSchool, Immersion, ImmersionUser, Slot, Training, UniversityYear,
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """
    def handle(self, *args, **options):
        success = "%s : %s" % (_("Annual statistics"), _("success"))

        try:
            year = UniversityYear.objects.get(active=True)
        except UniversityYear.DoesNotExist:
            msg = _("No active year found, can't update statistics")
            logger.error(msg)
            raise CommandError(msg)

        try:
            annual_stats = AnnualStatistics.objects.get(year=year.label)
        except AnnualStatistics.DoesNotExist:
            annual_stats = AnnualStatistics.objects.create(year=year.label)

        hs_queryset = HighSchool.objects\
            .prefetch_related('student_records')\
            .filter(convention_start_date__isnull=False, convention_end_date__isnull=False)

        # Approved high schools
        annual_stats.approved_highschools = hs_queryset.count()

        # Approved high schools with no registered students
        annual_stats.highschools_without_students = hs_queryset.filter(student_records__isnull=True).count()

        # Total number of registered students + high school pupils
        annual_stats.platform_registrations = ImmersionUser.objects\
            .prefetch_related('student_record', 'high_school_student_record', 'visitor_record')\
            .filter(
                Q(student_record__isnull=False)
                | Q(visitor_record__validation=2)
                | Q(high_school_student_record__validation=2)
            )\
            .distinct()\
            .count()

        # Number of registered students to at least one course immersion
        annual_stats.one_immersion_registrations = ImmersionUser.objects \
            .prefetch_related('immersions__slot__course')\
            .filter(
                immersions__isnull=False,
                immersions__slot__course__isnull=False,
                immersions__cancellation_type__isnull=True
            )\
            .distinct().count()

        # Number of registered students to more than one immersion
        annual_stats.multiple_immersions_registrations = ImmersionUser.objects\
            .prefetch_related('immersions__slot__course')\
            .annotate(
                imm_count=Count(
                    'immersions',
                    filter=Q(immersions__cancellation_type__isnull=True, immersions__slot__course__isnull=False,))
                )\
            .filter(imm_count__gt=1).count()

        # User with no course immersion registration
        annual_stats.no_course_immersions_registrations = ImmersionUser.objects\
            .prefetch_related('immersions__slot__course') \
            .filter(
                Q(student_record__isnull=False)
                | Q(visitor_record__validation=2)
                | Q(high_school_student_record__validation=2)
            ) \
            .annotate(
                imm_count=Count(
                    'immersions',
                    filter=Q(immersions__slot__course__isnull=False))
                )\
            .filter(imm_count=0).count()

        # Number of course immersions registrations
        annual_stats.immersion_registrations = Immersion.objects.\
            prefetch_related('slot__course')\
            .filter(
                cancellation_type__isnull=True,
                slot__course__isnull=False,
            ).count()

        # Number of participations to courses immersions
        annual_stats.immersion_participations = Immersion.objects. \
            prefetch_related('slot__course') \
            .filter(
                cancellation_type__isnull=True,
                attendance_status=1,
                slot__course__isnull=False,
            ).count()

        # Number of participants in at least one immersion
        annual_stats.participants_one_immersion = ImmersionUser.objects.filter(
            immersions__attendance_status=1
        ).distinct().count()

        # Course immersions participations ratio
        if annual_stats.immersion_registrations:
            annual_stats.immersion_participation_ratio = round(
                (annual_stats.immersion_participations / annual_stats.immersion_registrations) * 100,
                2
            )
        else:
            annual_stats.immersion_participation_ratio = 0

        # Number of participants in more than one immersion
        annual_stats.participants_multiple_immersions = ImmersionUser.objects.annotate(
            imm_count=Count('immersions', filter=Q(immersions__attendance_status=1))).filter(
            imm_count__gt=1).count()

        # Structures with published slots
        annual_stats.structures_count = Structure.objects.filter(active=True).annotate(
            slot_nb=Count('courses__slots', filter=Q(courses__slots__published=True))) \
            .filter(slot_nb__gt=0).count()

        # Active trainings
        annual_stats.active_trainings_count = Training.objects.filter(active=True).count()

        # Trainings with at least one slot
        annual_stats.trainings_one_slot_count = Training.objects.filter(active=True).annotate(
            slot_nb=Count('courses__slots', filter=Q(courses__slots__published=True))) \
            .filter(slot_nb__gt=0).count()

        # Active courses
        annual_stats.active_courses_count = Course.objects.filter(published=True).count()

        # Courses with at least one slot
        annual_stats.courses_one_slot_count = Course.objects.annotate(
            slot_nb=Count('slots', filter=Q(slots__published=True))) \
            .filter(slot_nb__gt=0).count()

        # Published course slots
        annual_stats.total_slots_count = Slot.objects.filter(course__isnull=False, published=True).count()

        # Number of offered seats of course slots
        annual_stats.seats_count = Slot.objects.filter(course__isnull=False, published=True).aggregate(
            seats_count=Sum('n_places'))['seats_count'] or 0

        annual_stats.save()

        logger.info(success)
        return success
