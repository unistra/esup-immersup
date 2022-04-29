import os
import socket
from os import environ
from os.path import normpath

from .base import *

#######################
# Debug configuration #
#######################

DEBUG = environ.get('DEBUG', True)


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
DATABASES['default']['USER'] = environ.get('DEFAULT_DB_USER', 'immersup')
DATABASES['default']['PASSWORD'] = environ.get('DEFAULT_DB_PASSWORD', 'immersup')
DATABASES['default']['NAME'] = environ.get('DEFAULT_DB_NAME', 'immersup')
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

CAS_SERVER_URL = environ.get('CAS_SERVER_URL', 'https://cas-dev.unistra.fr/cas/')
CAS_LOGOUT_REQUEST_ALLOWED = environ.get('CAS_LOGOUT_REQUEST_ALLOWED', ('cas-dev.unistra.fr', 'cas-dev.unistra.fr'))
CAS_FORCE_SSL_SERVICE_URL = environ.get('CAS_FORCE_SSL_SERVICE_URL', False)

############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

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

EMAIL_BACKEND = environ.get('EMAIL_BACKEND', 'immersionlyceens.libs.mails.backends.ConsoleBackend')
FORCE_EMAIL = environ.get('FORCE_EMAIL', '')
# FORCE_EMAIL_ADDRESS = "appli-immersionlyceens-test@unistra.fr"
DEFAULT_FROM_EMAIL = environ.get('DEFAULT_FROM_EMAIL', 'no-reply@%s' % socket.getfqdn())


# SUMMER NOTE
BASE_DIR = os.getcwd()
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')
SUMMERNOTE_THEME = 'bs4'
SUMMERNOTE_CONFIG = {
    'spellCheck': True,
    'iframe': True,
    'summernote': {
        'lang': 'fr-FR',
    },
    'codeviewIframeFilter': True,
    'disable_attachment': True,
    'toolbar': [
        [
            'style',
            [
                'style',
                'bold',
                'italic',
                'underline',
                'strikethrough',
                'superscript',
                'subscript',
                'clear',
            ]
        ],
        [
            'font',
            [
                'fontsize',
                'forecolor',
                'paragraph',
            ]
        ],
        [
            'misc',
            [
                'ol',
                'ul',
                'height',
            ],
        ],
        [
            'others',
            [
                'link',
                'table',
                'hr'
            ],
        ],
        [
            'view',
            [
                'codeview',
                'undo',
                'redo',
                'fullscreen'
            ],
        ],
    ],
    'popover': {
        'link': ['link', ['linkDialogShow', 'unlink']],
        'table': [
            [
                'add',
                [
                    'addRowDown',
                    'addRowUp',
                    'addColLeft',
                    'addColRight'
                ]
            ],
            [
                'delete',
                [
                    'deleteRow',
                    'deleteCol',
                    'deleteTable'
                ]
            ],
        ],
    }
}

# Mailing list subscriber files directory
BASE_FILES_DIR = "/tmp"
MAILING_LIST_FILES_DIR = join(BASE_FILES_DIR, 'mailing_lists')

# Use Unistra theme & css
UNISTRA = environ.get('USE_UNISTRA_THEME', True)
