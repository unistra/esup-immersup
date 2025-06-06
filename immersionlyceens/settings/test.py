import os
import socket
from os import environ
from os.path import normpath, join, isdir

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

#######################
# Debug configuration #
#######################

DEBUG = False


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
    '.u-strasbg.fr',
    '.unistra.fr',
]

CSRF_TRUSTED_ORIGINS = [
    '{{ csrf_trusted_origins }}',
]

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

#####################
# Log configuration #
#####################

LOGGING['handlers']['file']['filename'] = '{{ remote_current_path }}/log/app.log'

for logger in LOGGING['loggers']:
    LOGGING['loggers'][logger]['level'] = 'DEBUG'


####################
#       CAS        #
####################
USE_CAS = False
CAS_REDIRECT_URL = '{{ cas_redirect_url }}'
CAS_SERVER_URL = 'https://cas.unistra.fr:443/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas1.di.unistra.fr', 'cas2.di.unistra.fr')
# CAS_SERVER_URL = 'https://cas-pprd.unistra.fr:443/cas/'
# CAS_LOGOUT_REQUEST_ALLOWED = ('cas-w1-pprd.di.unistra.fr', 'cas-w2-pprd.di.unistra.fr')
CAS_FORCE_SSL_SERVICE_URL = True


####################
#    SHIBBOLETH    #
####################
# EDUCONNECT_LOGIN_URL = "https://pr4.educonnect.phm.education.gouv.fr/idp/profile/SAML2/Unsolicited/SSO"
EDUCONNECT_LOGIN_URL = "https://pr4.educonnect.phm.education.gouv.fr/idp"
EDUCONNECT_LOGOUT_URL = "https://pr4.educonnect.phm.education.gouv.fr/logout"

# AGENT_FEDERATION_LOGIN_URL = "https://hub-pr2.phm.education.gouv.fr/idp/profile/SAML2/Unsolicited/SSO"
AGENT_FEDERATION_LOGIN_URL = "https://hub-pr2.phm.education.gouv.fr/idp"
AGENT_FEDERATION_LOGOUT_URL = "https://hub-pr2.phm.education.gouv.fr/logout"


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
EMAIL_SSL_ON_CONNECT = '{{ email_ssl_on_connect }}'.lower() == 'true'
EMAIL_PORT = '{{ email_port }}'
EMAIL_HOST_USER = '{{ email_host_user }}'
EMAIL_HOST_PASSWORD = '{{ email_host_password }}'

FORCE_EMAIL_ADDRESS = '{{ force_email_address }}'
DEFAULT_FROM_EMAIL = '{{ default_from_email }}'


###############
# Sentry init #
###############

# TODO: add boolean to deactivate sentry integration ???
RELEASE = '{{ release }}'
sentry_sdk.init(
    dsn="https://068693b77bd442eaa28c842d8c2ebb38@sentry.app.unistra.fr/34",
    integrations=[DjangoIntegration()],
    environment="test",
    release=RELEASE,
)

# Goal
STAGE = 'Test'

#####################
# S3 storage config #
#####################
# Uncomment/comment below switching to s3 media (uploads) file storage
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None
AWS_ACCESS_KEY_ID = '{{ s3_access_key }}'
AWS_SECRET_ACCESS_KEY = '{{ s3_secret_key }}'
AWS_STORAGE_BUCKET_NAME = '{{ s3_bucket }}'
AWS_S3_ENDPOINT_URL = '{{ s3_endpoint }}'
S3_FILEPATH = 'test'

##########
# Matomo #
##########
# FIXME: testing for now, will be removed later !
USE_MATOMO = True
MATOMO_URL = '{{ matomo_url }}'
MATOMO_SITE_ID = '{{ matomo_site_id }}'

# Use Unistra theme & css
# true to use unistra theme (fake boolean ftw)
UNISTRA = '{{ use_unistra_theme }}'

STATICFILES_STORAGE = 'immersionlyceens.storage.ManifestStaticFilesStorageWithoutSourceMap'


# Extra locales
EXTRA_LOCALE_PATH = '{{ extra_locale_path }}'

if EXTRA_LOCALE_PATH:
    EXTRA_LOCALE_DIR = normpath(join(DJANGO_ROOT, EXTRA_LOCALE_PATH))

    if isdir(EXTRA_LOCALE_DIR):
        LOCALE_PATHS = [EXTRA_LOCALE_DIR] + LOCALE_PATHS


###########################
#  SEARCH PLUGIN FOR UAI  #
###########################
UAI_API_URL = "{{ uai_api_url }}"
UAI_API_AUTH_HEADER = "{{ uai_api_auth_header }}"
UAI_API_SEARCH_ATTR = "{{ uai_api_search_attr }}"

