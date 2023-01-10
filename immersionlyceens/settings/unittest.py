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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': environ.get('DEFAULT_DB_NAME', 'immersionlyceens'),
        'USER': environ.get('DEFAULT_DB_USER', 'immersionlyceens'),
        'PASSWORD': environ.get('DEFAULT_DB_PASSWORD', 'immersionlyceens'),
        'HOST': environ.get('DEFAULT_DB_HOST', 'postgres'),
        'PORT': environ.get('DEFAULT_DB_PORT', '5432'),
        'TEST':  {
            'NAME': None,
            'CHARSET': "UTF-8' LC_COLLATE 'C' LC_CTYPE 'C",
            'TEMPLATE': "template0",
        }
    }
}

############################
# Allowed hosts & Security #
############################

ALLOWED_HOSTS = [
    '*'
]

# Language code for unit tests
del(LANGUAGE_CODE)

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

#######################
# Email configuration #
#######################
EMAIL_BACKEND = 'immersionlyceens.libs.mails.backends.DummyBackend'

