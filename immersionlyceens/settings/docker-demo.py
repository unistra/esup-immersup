import os
import socket
from os import environ
from os.path import join, normpath

from .base import *

##########################
# Database configuration #
##########################

DATABASES['default']['HOST'] = environ.get('DEFAULT_DB_HOST', 'localhost')
DATABASES['default']['USER'] = environ.get('DEFAULT_DB_USER', 'immersup_demo')
DATABASES['default']['PASSWORD'] = environ.get('DEFAULT_DB_PASSWORD', 'immersup_demo')
DATABASES['default']['NAME'] = environ.get('DEFAULT_DB_NAME', 'immersup_demo')
DATABASES['default']['PORT'] = environ.get('DEFAULT_DB_PORT', '5432')


############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = environ.get('DJANGO_ALLOWED_HOSTS', '*').split(',')

#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'ssl')


#####################
# Log configuration #
#####################

LOGGING['handlers']['file']['filename'] = environ.get('LOG_PATH', '/tmp/log')

##############
# Secret key #
##############

SECRET_KEY = environ.get('SECRET_KEY', '8655fd634a264e3ca7bf60ed41617ce8')


####################
#       CAS        #
####################

CAS_REDIRECT_URL = environ.get('CAS_REDIRECT_URL', '/')
CAS_FORCE_SSL_SERVICE_URL = environ.get('CAS_FORCE_SSL_SERVICE_URL', False)
CAS_SERVER_URL = environ.get('CAS_SERVER_URL', 'https://cas-dev.unistra.fr/cas/')

#################
# APIs settings #
#################

WITH_HOLIDAY_API = environ.get('WITH_HOLIDAY_API', True)
HOLIDAY_API_URL = environ.get('HOLIDAY_API_URL', 'http://rest-api.u-strasbg.fr/holidays/alsace-moselle/{year}.json')
HOLIDAY_API_MAP = environ.get('HOLIDAY_API_MAP', "{'date': 'date', 'label': 'nom_jour_ferie'}")
HOLIDAY_API_DATE_FORMAT = environ.get('HOLIDAY_API_DATE_FORMAT', '%Y-%m-%d')

# SUMMER NOTE
MEDIA_URL = '/media/'

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
MEDIA_ROOT = environ.get('MEDIA_ROOT', 'mediafiles')


#######################
# Email configuration #
#######################

DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL', 'support@unistra.fr')

# EMAIL_BACKEND choices :
#     - immersionlyceens.libs.mails.backends.EmailBackend
#     - immersionlyceens.libs.mails.backends.ConsoleBackend
#     - immersionlyceens.libs.mails.backends.FileBackend
EMAIL_BACKEND = environ.get('EMAIL_BACKEND', 'immersionlyceens.libs.mails.backends.EmailBackend')
EMAIL_HOST = environ.get('EMAIL_HOST', '0.0.0.0')
FROM_ADDR = environ.get('FROM_ADDR', 'no.reply@unistra.fr')
FORCE_EMAIL_ADDRESS = environ.get('FORCE_EMAIL_ADDRESS', None)

STATIC_ROOT = normpath(join(SITE_ROOT, 'staticfiles'))
STATIC_URL = '/static/'

# Use Unistra theme & css
UNISTRA = environ.get('USE_UNISTRA_THEME', 'true')
