from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class UserConfig(AppConfig):
    name = 'immersionlyceens.apps.user'
    verbose_name = _('Users')
