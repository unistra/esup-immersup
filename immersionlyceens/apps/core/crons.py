import logging

from django.core import management
from django.utils import timezone

from django_cron import CronJobBase, Schedule

from immersionlyceens.apps.core.models import ScheduledTask

logger = logging.getLogger(__name__)



class CronTest(CronJobBase):
    """
    RUN_EVERY_MINS = 2 # every 10 minutes
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    """
    run = False
    week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # TODO : add parameter checks

    schedule = None
    code = 'core.cron_test'    # a unique code

    def __init__(self):
        super().__init__()
        task = None
        schedule_params = {}

        try:
            task = ScheduledTask.objects.get(command_name="crontest")
        except ScheduledTask.DoesNotExist:
            pass

        if task:
            if task.time:
                schedule_params['run_at_times'] = [task.time.strftime("%H:%M")]

            run_on_days = []

            for week_day in range(0, 7):
                if getattr(task, self.week_days[week_day]):
                    run_on_days.append(week_day)

            if run_on_days:
                schedule_params['run_on_days'] = run_on_days

            self.schedule = Schedule(**schedule_params)
            self.run = True

    def do(self):
        if self.run:
            try:
                management.call_command("crontest", verbosity=0)
            except Exception as e:
                logger.error("Cannot run command crontest : %s" % e)
