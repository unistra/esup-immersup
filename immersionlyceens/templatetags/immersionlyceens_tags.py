import re
from decimal import Decimal

from django import template
from django.conf import settings
from django.contrib.auth import BACKEND_SESSION_KEY
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.formats import number_format
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from immersionlyceens.libs.utils import (
    get_custom_favicon_url, get_general_setting, get_information_text,
)

from ..apps.core.models import GeneralSettings, HighSchool, ImmersionUser

register = template.Library()


@register.filter
def redify(value, redvalue):
    return '<span class="red">%s</span>' % value if value == _(redvalue) else value


@register.filter
def redorgreenify(value, redvalue):
    color = "green" if value == _(redvalue) else "red"
    return f'<span class="{color}">{value}</span>'


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
    except (ValueError, NameError):
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


@register.simple_tag
def information_text_get(code):
    try:
        return get_information_text(code=code)
    except (ValueError, NameError):
        return ""


@register.filter
def fix_lang_code(code):
    # Dirty fix for safari and old browsers
    if code == 'fr-fr' or code =='fr':
        return 'fr-FR'
    # TODO: other languages here ?
    else:
        return code


@register.filter()
def grouper_sort(grouper):
    grouper.sort(key=grouper)
    return grouper


@register.filter()
def grouper_sort_reversed(grouper):
    grouper.sort(reverse=True)
    return grouper


@register.simple_tag(takes_context = True)
def get_logout_url(context):
    backend = context.request.session.get(BACKEND_SESSION_KEY)

    #TODO: check if other backends needed and use them
    if backend == 'django_cas.backends.CASBackend':
        return reverse('django_cas:logout')
    elif backend == 'shibboleth.backends.ShibbolethRemoteUserBackend':
        return reverse('shibboleth:logout')
    # TODO: check urls.py accounts namespace is using django_cas for now
    elif backend == 'django.contrib.auth.backends.ModelBackend':
        return reverse('django_cas:logout')
    else:
        return ''

@register.simple_tag(takes_context = True)
def is_local_superuser(context):
    #TODO: check if other backends needed and use them
    return context.request.session[BACKEND_SESSION_KEY] \
        not in ('shibboleth.backends.ShibbolethRemoteUserBackend', 'django_cas.backends.CASBackend') \
        and context.request.user.is_superuser


@register.filter()
def sub(value, arg):
    return value - arg

@register.filter()
def get_etab_label(obj):
    try:
        return f'{obj.label} - {obj.city}' if isinstance(obj, HighSchool) else obj.label
    except Exception as e:
        return ""

@register.simple_tag
def get_custom_favicon():
    try:
        return get_custom_favicon_url()
    except (ValueError, NameError):
        return ""
