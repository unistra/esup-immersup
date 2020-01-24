# -*- coding: utf-8 -*-

from os import environ
from os.path import normpath
from .base import *

#######################
# Debug configuration #
#######################

DEBUG = True


##########################
# Database configuration #
##########################

DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
DATABASES['default']['NAME'] = environ.get('DEFAULT_DB_NAME', 'immersionlyceens.db')

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
        normpath(join('/tmp', 'test_%s.log' % SITE_NAME)))
LOGGING['handlers']['file']['level'] = 'DEBUG'

for logger in LOGGING['loggers']:
    LOGGING['loggers'][logger]['level'] = 'DEBUG'

TEST_RUNNER = 'django.test.runner.DiscoverRunner'


WITH_HOLIDAY_API = True
HOLIDAY_API_URL = 'http://rest-api.u-strasbg.fr/holidays/alsace-moselle/{year}.json'
HOLIDAY_API_MAP = {
    'date': 'date',
    'label': 'nom_jour_ferie'
}
HOLIDAY_API_DATE_FORMAT = '%Y-%m-%d'


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