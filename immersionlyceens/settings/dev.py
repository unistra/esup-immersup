# -*- coding: utf-8 -*-

import os
from os import environ
from os.path import normpath
import socket

from .base import *

#######################
# Debug configuration #
#######################

DEBUG = True


##########################
# Database configuration #
##########################

# In your virtualenv, edit the file $VIRTUAL_ENV/bin/postactivate and set
# properly the environnement variable defined in this file (ie: os.environ[KEY])
# ex: export DEFAULT_DB_NAME='project_name'

# Default values for default database are :
# engine : sqlite3
# name : PROJECT_ROOT_DIR/default.db

DATABASES['default']['HOST'] = environ.get('DEFAULT_DB_HOST', 'localhost')
DATABASES['default']['USER'] = environ.get('DEFAULT_DB_USER', '')
DATABASES['default']['PASSWORD'] = environ.get('DEFAULT_DB_PASSWORD', '')
DATABASES['default']['NAME'] = environ.get('DEFAULT_DB_NAME', '')
DATABASES['default']['PORT'] = environ.get('DEFAULT_DB_PORT', '5432')

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': 'db.sqlite3',
#     }
# }

########################
#     CAS SETTINGS     #
########################
CAS_SERVER_URL = 'https://cas-dev.unistra.fr/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas-dev.unistra.fr', 'cas-dev.unistra.fr')
CAS_FORCE_SSL_SERVICE_URL = False

############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = [
    '*'
]

#####################
# Log configuration #
#####################

LOGGING['handlers']['file']['filename'] = environ.get('LOG_DIR',
        normpath(join('/tmp', '%s.log' % SITE_NAME)))
LOGGING['handlers']['file']['level'] = 'DEBUG'

for logger in LOGGING['loggers']:
    LOGGING['loggers'][logger]['level'] = 'DEBUG'


###########################
# Unit test configuration #
###########################

INSTALLED_APPS += [
    'coverage',
    'debug_toolbar',
]


#################
# Debug toolbar #
#################

DEBUG_TOOLBAR_PATCH_SETTINGS = False
MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]
INTERNAL_IPS = ['127.0.0.1', '0.0.0.0']

#################
# APIs settings #
#################

ACCOUNTS_CLIENT = 'immersionlyceens.libs.api.accounts.LdapAPI'


#####################
# LDAP API settings #
#####################

# Server
LDAP_API_HOST = environ.get('LDAP_API_HOST', '')
LDAP_API_PORT = environ.get('LDAP_API_PORT', '')
LDAP_API_DN = environ.get('LDAP_API_DN', '')
LDAP_API_PASSWORD = environ.get('LDAP_API_PASSWORD', '')
LDAP_API_BASE_DN = environ.get('LDAP_API_BASE_DN', '')

# Filters and attributes
LDAP_API_ACCOUNTS_FILTER = environ.get('LDAP_API_ACCOUNTS_FILTER', '')
LDAP_API_SEARCH_ATTR = environ.get('LDAP_API_SEARCH_ATTR', '')
LDAP_API_DISPLAY_ATTR = environ.get('LDAP_API_DISPLAY_ATTR', '')
LDAP_API_EMAIL_ATTR = environ.get('LDAP_API_EMAIL_ATTR', '')
LDAP_API_USERNAME_ATTR = environ.get('LDAP_API_USERNAME_ATTR', '')
LDAP_API_LASTNAME_ATTR = environ.get('LDAP_API_LASTNAME_ATTR', '')
LDAP_API_FIRSTNAME_ATTR = environ.get('LDAP_API_FIRSTNAME_ATTR', '')

WITH_HOLIDAY_API = True
HOLIDAY_API_URL = 'http://rest-api.u-strasbg.fr/holidays/alsace-moselle/{year}.json'
HOLIDAY_API_MAP = {
    'date': 'date',
    'label': 'nom_jour_ferie'
}
HOLIDAY_API_DATE_FORMAT = '%Y-%m-%d'

#######################
# Email configuration #
#######################

EMAIL_BACKEND = 'immersionlyceens.libs.mails.backends.ConsoleBackend'
# FORCE_EMAIL_ADDRESS = "appli-immersionlyceens-test@unistra.fr"
DEFAULT_FROM_EMAIL = 'no-reply@%s' % socket.getfqdn()


# Mailing list subscriber files directory
BASE_FILES_DIR = "/tmp"
MAILING_LIST_FILES_DIR = join(BASE_FILES_DIR, 'mailing_lists')
