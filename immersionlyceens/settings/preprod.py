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

WITH_HOLIDAY_API = True
HOLIDAY_API_URL = 'http://rest-api.u-strasbg.fr/holidays/alsace-moselle/{year}.json'
HOLIDAY_API_MAP = {'date': 'date', 'label': 'nom_jour_ferie'}
HOLIDAY_API_DATE_FORMAT = '%Y-%m-%d'

#######################
# Email configuration #
#######################

EMAIL_BACKEND = 'immersionlyceens.libs.mails.backends.EmailBackend'
FORCE_EMAIL_ADDRESS = "appli-immersionlyceens-pprd@unistra.fr"
DEFAULT_FROM_EMAIL = 'no-reply@%s' % socket.getfqdn()

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
    environment="preprod",
    release=RELEASE,
)
