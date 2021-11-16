import re

from django.core.management import BaseCommand

from immersionlyceens.apps.core.models import MailTemplate, MailTemplateVars


class Command(BaseCommand):
    # ${ my_var } ==> {{ my_var }}
    old: str = r"\$\{[ ]*(?P<variable>(\w|\.)*)[ ]*}"
    new: str = r"{{ \g<variable> }}"
    help = "Convert ImmerSup mail template from old variable template to new."

    def handle(self, *args, **options) -> None:
        print("Hello world")

        mail_templates: MailTemplate = MailTemplate.objects.all()
        print("Mail templates:")
        for mail_template in mail_templates:
            mail_template.body = self.convert(mail_template.body)
            mail_template.save()
            print(f"- {mail_template}")

        print()
        print()
        print("Variables:")
        mail_template_var = MailTemplateVars.objects.all()
        for var in mail_template_var:
            var.code = self.convert(var.code)
            var.save()
            print(f"- {var}")





    def convert(self, text: str) -> str:
        return re.sub(self.old, self.new, text)
