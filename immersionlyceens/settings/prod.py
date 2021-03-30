# -*- coding: utf-8 -*-

import os
import socket
from os import environ
from os.path import normpath

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

##########################
# Database configuration #
##########################

DATABASES['default']['HOST'] = '{{ default_db_host }}'
DATABASES['default']['USER'] = '{{ default_db_user }}'
DATABASES['default']['PASSWORD'] = '{{ default_db_password }}'
DATABASES['default']['NAME'] = '{{ default_db_name }}'


############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = [
    '.u-strasbg.fr',
    '.unistra.fr',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'ssl')


#####################
# Log configuration #
#####################

LOGGING['handlers']['file']['filename'] = '{{ remote_current_path }}/log/app.log'

##############
# Secret key #
##############

SECRET_KEY = '{{ secret_key }}'


####################
#       CAS        #
####################

CAS_REDIRECT_URL = '{{ cas_redirect_url }}'
CAS_FORCE_SSL_SERVICE_URL = True


#################
# APIs settings #
#################

# Feel free to implement your own accounts search functions and
# enter your plugin name here :)

ACCOUNTS_CLIENT = 'immersionlyceens.libs.api.accounts.LdapAPI'


#####################
# LDAP API settings #
#####################

# Server
LDAP_API_HOST = '{{ ldap_api_host }}'
LDAP_API_PORT = '{{ ldap_api_port }}'
LDAP_API_DN = '{{ ldap_api_dn }}'
LDAP_API_PASSWORD = '{{ ldap_api_password }}'
LDAP_API_BASE_DN = '{{ ldap_api_base_dn }}'

# Filters and attributes
LDAP_API_ACCOUNTS_FILTER = '{{ ldap_api_accounts_filter }}'
LDAP_API_SEARCH_ATTR = '{{ ldap_api_search_attr }}'
LDAP_API_DISPLAY_ATTR = '{{ ldap_api_display_attr }}'
LDAP_API_EMAIL_ATTR = '{{ ldap_api_email_attr }}'
LDAP_API_USERNAME_ATTR = '{{ ldap_api_username_attr }}'
LDAP_API_LASTNAME_ATTR = '{{ ldap_api_lastname_attr }}'
LDAP_API_FIRSTNAME_ATTR = '{{ ldap_api_firstname_attr }}'

WITH_HOLIDAY_API = True
HOLIDAY_API_URL = 'http://rest-api.u-strasbg.fr/holidays/alsace-moselle/{year}.json'
HOLIDAY_API_MAP = {'date': 'date', 'label': 'nom_jour_ferie'}
HOLIDAY_API_DATE_FORMAT = '%Y-%m-%d'

#######################
# Email configuration #
#######################

# If needed

#######################

# SUMMER NOTE
BASE_DIR = os.getcwd()
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
SUMMERNOTE_THEME = 'bs4'
SUMMERNOTE_CONFIG = {
    'spellCheck': True,
    'iframe': True,
    'summernote': {'lang': 'fr-FR', },
    'codeviewIframeFilter': True,
    'disable_attachment': True,
    'toolbar': [
        ['style', ['style', 'bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript', 'clear', ], ],
        ['font', ['fontsize', 'forecolor', 'paragraph', ]],
        ['misc', ['ol', 'ul', 'height', ], ],
        ['others', ['link', 'table', 'hr'], ],
        ['view', ['codeview', 'undo', 'redo', 'fullscreen'], ],
    ],
    'popover': {
        'link': ['link', ['linkDialogShow', 'unlink']],
        'table': [
            ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
            ['delete', ['deleteRow', 'deleteCol', 'deleteTable']],
        ],
    },
}

########################
# UPLOAD configuration #
########################

# url for logos upload
MEDIA_ROOT = '/nfs/immersion'

# Mailing list subscriber files directory
BASE_FILES_DIR = '{{ base_files_dir }}'
MAILING_LIST_FILES_DIR = join(BASE_FILES_DIR, 'mailing_lists')

###############
# Sentry init #
###############

# TODO: add boolean to deactivate sentry integration ???
RELEASE = '{{ release }}'
sentry_sdk.init(
    dsn="https://068693b77bd442eaa28c842d8c2ebb38@sentry.app.unistra.fr/34",
    integrations=[DjangoIntegration()],
    environment="prod",
    release=RELEASE,
)
