from django.core import management
from django_cron import CronJobBase, Schedule

class CronTest(CronJobBase):
    RUN_EVERY_MINS = 5 # every 10 minutes

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'core.cron_test'    # a unique code

    def do(self):
        management.call_command("crontest", verbosity=0)
