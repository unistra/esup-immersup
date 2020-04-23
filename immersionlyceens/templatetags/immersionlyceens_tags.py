import re
from decimal import Decimal

from django import template
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils.encoding import force_text
from django.utils.formats import number_format
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from immersionlyceens.libs.utils import get_general_setting

# TODO: uncomment later
from ..apps.core.models import GeneralSettings, ImmersionUser

register = template.Library()


@register.filter
def redify(value, redvalue):
    return '<span class="red">%s</span>' % value if value == _(redvalue) else value


@register.filter
def redorgreenify(value, redvalue):
    color = "green" if value == _(redvalue) else "red"
    return '<span class="%s">%s</span>' % (color, value)


@register.simple_tag
def get_bootstrap_alert_msg_css_name(tags):
    # in bootstrap the class danger is for error !!!
    return 'danger' if tags == 'error' else tags


@register.simple_tag
def settings_get(name):
    try:
        return str(settings.__getattr__(name))
    except Exception:
        return ""


@register.simple_tag
def general_settings_get(name):
    try:
        return get_general_setting(name=name)
    except ValueError:
        return ""


@register.filter(name='has_group')
def has_group(user, group_name):
    return user.has_groups(group_name)


@register.filter
def null_value(value):
    return value or "&nbsp;"


@register.filter(name='keyvalue')
def keyvalue(dict, key):
    return dict[key] if key in dict else ""


@register.filter(name='in_list')
def in_list(value, the_list):
    value = str(value)
    return value in the_list.split(',')


@register.tag
def immersion_users(parser, token):
    return UserNode()


class UserNode(template.Node):
    def render(self, context):
        # TODO: uncomment
        context['immersion_users'] = ImmersionUser.objects.all().order_by('username')
        return ''


@register.tag
def authorized_groups(parser, token):
    tag_name, user = token.split_contents()
    return AuthorizedGroupsNode(user)


class AuthorizedGroupsNode(template.Node):
    def __init__(self, user):
        self.user = template.Variable(user)

    def render(self, context):
        user = self.user.resolve(context)

        # User should not be an anonymous one !!!
        if user.id is not None:
            context['authorized_groups'] = {g.name for g in user.authorized_groups()}
        else:
            context['authorized_groups'] = set()

        return ''


@register.filter
def in_groups(value, args):
    value = value or set()
    return value & set(args.split(','))
