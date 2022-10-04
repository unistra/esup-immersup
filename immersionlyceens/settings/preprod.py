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

# PostgreSQL unaccent extension
POSTGRESQL_ADD_UNACCENT_EXTENSION = False # For migration file
POSTGRESQL_HAS_UNACCENT_EXTENSION = True # For queries

############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = [
    '*',
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
USE_CAS = False

CAS_REDIRECT_URL = '{{ cas_redirect_url }}'
CAS_SERVER_URL = 'https://cas.unistra.fr:443/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas1.di.unistra.fr', 'cas2.di.unistra.fr')
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

EMAIL_HOST = '{{ email_host }}'
EMAIL_USE_TLS = '{{ email_use_tls }}'.lower() == 'true'
EMAIL_PORT = '{{ email_port }}'
EMAIL_HOST_USER = '{{ email_host_user }}'
EMAIL_HOST_PASSWORD = '{{ email_host_password }}'

FORCE_EMAIL_ADDRESS = '{{ force_email_address }}'
DEFAULT_FROM_EMAIL = '{{ default_from_email }}'

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

# Goal
STAGE = 'Preprod'

#####################
# S3 storage config #
#####################
# Uncomment/comment below switching to s3 media (uploads) file storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_FILE_OVERWRITE = True
AWS_DEFAULT_ACL = None
AWS_AUTO_CREATE_BUCKET = True
AWS_ACCESS_KEY_ID = '{{ s3_access_key }}'
AWS_SECRET_ACCESS_KEY = '{{ s3_secret_key }}'
AWS_STORAGE_BUCKET_NAME = '{{ s3_bucket }}'
AWS_S3_ENDPOINT_URL = '{{ s3_endpoint }}'
S3_FILEPATH = 'preprod'

# Use Unistra theme & css
UNISTRA = '{{ use_unistra_theme }}'
##########
# Matomo #
##########
USE_MATOMO = True
MATOMO_URL = '{{ matomo_url }}'
MATOMO_SITE_ID = '{{ matomo_site_id }}'
