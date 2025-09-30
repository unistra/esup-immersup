"""
Run all Scheduled tasks
"""

import logging
import datetime
import math

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from immersionlyceens.apps.core.models import ScheduledTask, ScheduledTaskLog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            action='store',
            help=_('simulate cron running at <date> (for testing purpose). Format : MMDD'),
        )
        parser.add_argument(
            '--time',
            action='store',
            help=_('simulate cron running at <time> (for testing purpose). Format : HHMM'),
        )
    def handle(self, *args, **options):

        now = timezone.localtime().replace(second=0, microsecond=0)
        today = timezone.localdate()

        # Force with options
        date = options.get("date")
        time = options.get("time")

        if date:
            try:
                if len(date) != 4:
                    raise Exception(_('value length error'))

                month = int(date[0:2])
                day = int(date[2:4])
                today = datetime.date(today.year, month, day)
                self.stdout.write(_("Using date : %s") % today)
            except Exception as e:
                raise CommandError(_("date : bad argument format : %s") % e)

        if time:
            try:
                if len(time) != 4:
                    raise Exception(_('value length error'))

                hours = int(time[0:2])
                minutes = int(time[2:4])
                now = datetime.datetime.combine(datetime.date.today(), datetime.time(hours, minutes))
                now = now.replace(tzinfo=now.tzinfo)
                self.stdout.write(_("Using time : %s") % now)
            except Exception as e:
                raise CommandError(_("time : bad argument format : %s") % e)

        week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        for task in ScheduledTask.objects.filter(active=True):
            time_run = False
            freq_run = False

            command_name = task.command_name
            run_today = task.date == today or getattr(task, week_days[now.weekday()])

            if task.time:
                hour = task.time.hour
                minute = task.time.minute
                time_run = now.hour == hour and now.minute == minute
            else:
                # No execution time
                continue

            if task.frequency:
                # Convert time to datetime
                task_datetime = datetime.datetime.combine(datetime.date.today(), task.time)
                # add same timezone to allow comparison
                task_datetime = task_datetime.replace(tzinfo=now.tzinfo)
                # Get time delta and convert it in hours
                delta = (now - task_datetime).total_seconds()

                if now >= task_datetime and (delta / 3600) % task.frequency == 0:
                    freq_run = True

            if all([run_today, time_run or freq_run]):
                self.stdout.write(_("Running task : %s" % command_name))

                try:
                    # TODO : review all commands to add proper return values
                    ret = call_command(command_name, verbosity=0)
                    ScheduledTaskLog.objects.create(
                        task=task,
                        success=True,
                        message=ret
                    )
                except Exception as e:
                    logger.error("Cannot run command %s : %s" % (command_name, e))
                    ScheduledTaskLog.objects.create(
                        task=task,
                        success=False,
                        message=str(e)
                    )
