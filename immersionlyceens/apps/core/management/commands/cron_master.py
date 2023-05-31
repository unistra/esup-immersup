import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from immersionlyceens.apps.core.models import ScheduledTask, ScheduledTaskLog

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    """

    def handle(self, *args, **options):
        now = timezone.localtime()
        week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

        for task in ScheduledTask.objects.filter(active=True):
            command_name = task.command_name
            run_today = getattr(task, week_days[now.weekday()])

            if task.time:
                hour = task.time.hour
                minute = task.time.minute
            else:
                # if task.frequency:
                # Nothing to do
                return

            if all([run_today, now.hour == hour, now.minute == minute]):
                try:
                    # TODO : review all commands to add proper return values
                    ret = call_command(command_name, verbosity=0)
                    ScheduledTaskLog.objects.create(
                        task=task,
                        success=True
                    )
                except Exception as e:
                    logger.error("Cannot run command %s : %s" % (self.command_name, e))
                    ScheduledTaskLog.objects.create(
                        task=task,
                        success=False,
                        message=str(e)
                    )



