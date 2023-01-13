import logging

from django.core import management
from django.utils import timezone

from django_cron import CronJobBase, Schedule

from immersionlyceens.apps.core.models import ScheduledTask

logger = logging.getLogger(__name__)


class CronBase(CronJobBase):
    run = False
    week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # TODO : add parameter checks
    schedule = None
    command_name = None
    job_code = None

    def __init__(self, job_code:str, command_name:str):
        super().__init__()
        schedule_params = {}

        self.code = job_code
        self.command_name = command_name.strip()

        if not self.command_name:
            return

        try:
            task = ScheduledTask.objects.get(command_name=self.command_name, active=True)
        except ScheduledTask.DoesNotExist:
            return

        if task.time:
            schedule_params['run_at_times'] = [task.time.strftime("%H:%M")]

        run_on_days = []

        for week_day in range(0, 7):
            if getattr(task, self.week_days[week_day]):
                run_on_days.append(week_day)

        if run_on_days:
            schedule_params['run_on_days'] = run_on_days

        if schedule_params:
            self.schedule = Schedule(**schedule_params)
            self.run = True

    def do(self):
        if self.run:
            try:
                management.call_command(self.command_name, verbosity=0)
            except Exception as e:
                logger.error("Cannot run command %s : %s" % (command_name, e))


class SendCourseAlertsCron(CronBase):
    def __init__(self):
        command_name = "send_course_alerts"
        job_code = "core.send_course_alerts"
        super().__init__(job_code, command_name)
        self.do()


class SendComponentsSlotsReminderCron(CronBase):
    def __init__(self):
        command_name = "send_components_slots_reminder"
        job_code = "core.send_components_slots_reminder"
        super().__init__(job_code, command_name)
        self.do()


class SendSpeakerSlotReminderCron(CronBase):
    def __init__(self):
        command_name = "send_speaker_slot_reminder"
        job_code = "core.send_speaker_slot_reminder"
        super().__init__(job_code, command_name)
        self.do()


class SendSlotReminderCron(CronBase):
    def __init__(self):
        command_name = "send_slot_reminder"
        job_code = "core.send_slot_reminder"
        super().__init__(job_code, command_name)
        self.do()


class SendSlotEvaluationMessageCron(CronBase):
    def __init__(self):
        command_name = "send_slot_evaluation_message"
        job_code = "core.send_slot_evaluation_message"
        super().__init__(job_code, command_name)
        self.do()


class SendGlobalEvaluationMessageCron(CronBase):
    def __init__(self):
        command_name = "send_global_evaluation_message"
        job_code = "core.send_global_evaluation_message"
        super().__init__(job_code, command_name)
        self.do()


class GenerateMailingListSubscribersFilesCron(CronBase):
    def __init__(self):
        command_name = "generate_mailing_list_subscribers_files"
        job_code = "core.generate_mailing_list_subscribers_files"
        super().__init__(job_code, command_name)
        self.do()


class SendPendingValidationsNotificationCron(CronBase):
    def __init__(self):
        command_name = "send_pending_validations_notification"
        job_code = "core.send_pending_validations_notification"
        super().__init__(job_code, command_name)
        self.do()


class DeleteUnactivatedAccountsCron(CronBase):
    def __init__(self):
        command_name = "delete_unactivated_accounts"
        job_code = "core.delete_unactivated_accounts"
        super().__init__(job_code, command_name)
        self.do()


