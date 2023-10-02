import os
import socket
from os import environ
from os.path import normpath, join, isdir

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
USE_CAS = True

CAS_SERVER_URL = 'https://cas-dev.unistra.fr/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas-dev.unistra.fr')
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

LOGGING['handlers']['file']['filename'] = environ.get('LOG_DIR', normpath(join('/tmp', '%s.log' % SITE_NAME)))
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


################
# API settings #
################

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
FORCE_EMAIL_ADDRESS = environ.get('FORCE_EMAIL_ADDRESS', 'whatever@domain.tld')

EMAIL_HOST = environ.get('EMAIL_HOST', '127.0.0.1')
EMAIL_USE_TLS = environ.get('EMAIL_USE_TLS', "false").lower() == 'true'
EMAIL_SSL_ON_CONNECT = environ.get('EMAIL_SSL_ON_CONNECT', "false").lower() == 'true'
EMAIL_PORT = environ.get('EMAIL_PORT', 25)
EMAIL_HOST_USER = environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = environ.get('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = 'no-reply@%s' % socket.getfqdn()

# Goal
STAGE = 'Dev'

#####################
# S3 storage config #
#####################

# Uncomment/comment below switching to s3 media (uploads) file storage
# DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
# AWS_S3_FILE_OVERWRITE = False
# AWS_DEFAULT_ACL = Nonew
# AWS_S3_ENDPOINT_URL = environ.get('AWS_S3_ENDPOINT_URL')
# AWS_STORAGE_BUCKET_NAME = environ.get('AWS_STORAGE_BUCKET_NAME', 'immersup')
# AWS_ACCESS_KEY_ID = environ.get('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = environ.get('AWS_SECRET_ACCESS_KEY')
# S3_FILEPATH = 'dev'

# Use Unistra theme & css
UNISTRA = environ.get('USE_UNISTRA_THEME', 'true')

# Extra locales
EXTRA_LOCALE_PATH = environ.get('EXTRA_LOCALE_PATH', '')

if EXTRA_LOCALE_PATH:
    EXTRA_LOCALE_DIR = normpath(join(DJANGO_ROOT, EXTRA_LOCALE_PATH))

    if isdir(EXTRA_LOCALE_DIR):
        LOCALE_PATHS = [ EXTRA_LOCALE_DIR ] + LOCALE_PATHS
    else:
        print(f"Warning : EXTRA_LOCALE_DIR {EXTRA_LOCALE_DIR} directory does not exist")
