# -*- coding: utf-8 -*-

from os.path import abspath, basename, dirname, join, normpath

from django.utils.translation import ugettext_lazy as _

######################
# Path configuration #
######################

DJANGO_ROOT = dirname(dirname(abspath(__file__)))
SITE_ROOT = dirname(DJANGO_ROOT)
SITE_NAME = basename(DJANGO_ROOT)


#######################
# Debug configuration #
#######################

DEBUG = False
TEMPLATE_DEBUG = DEBUG


##########################
# Manager configurations #
##########################

ADMINS = [
    # ('Your Name', 'your_email@example.com'),
]

MANAGERS = ADMINS


##########################
# Database configuration #
##########################

# In your virtualenv, edit the file $VIRTUAL_ENV/bin/postactivate and set
# properly the environnement variable defined in this file (ie: os.environ[KEY])
# ex: export DEFAULT_DB_USER='immersionlyceens'

# Default values for default database are :
# engine : sqlite3
# name : PROJECT_ROOT_DIR/immersionlyceens.db

# defaut db connection
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'immersionlyceens',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '5432',
    }
}


######################
# Site configuration #
######################

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.11/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []


#########################
# General configuration #
#########################

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Paris'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fr-FR'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True


#######################
# locale configuration #
#######################

LOCALE_PATHS = [
    normpath(join(DJANGO_ROOT, 'locale')),
]


#######################
# Media configuration #
#######################

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = normpath(join(DJANGO_ROOT, 'media'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'


##############################
# Static files configuration #
##############################

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/site_media/'

# Additional locations of static files
STATICFILES_DIRS = [
    normpath(join(DJANGO_ROOT, 'static')),
]

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]


##############
# Secret key #
##############

# Make this unique, and don't share it with anybody.
# Only for dev and test environnement. Should be redefined for production
# environnement
SECRET_KEY = 'ma8r116)33!-#pty4!sht8tsa(1bfe%(+!&9xfack+2e9alah!'


##########################
# Template configuration #
##########################

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
        },
    },
]


############################
# Middleware configuration #
############################

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_cas.middleware.CASMiddleware',
    'shibboleth.middleware.ShibbolethRemoteUserMiddleware',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_cas.backends.CASBackend',
    'shibboleth.backends.ShibbolethRemoteUserBackend',
)

######################
#   Authentication   #
######################

AUTH_USER_MODEL = "core.ImmersionUser"


#####################
#       CAS         #
#####################

CAS_SERVER_URL = 'https://cas.unistra.fr:443/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas1.di.unistra.fr', 'cas2.di.unistra.fr')
CAS_USER_CREATION = False
CAS_IGNORE_REFERER = True
CAS_REDIRECT_URL = '/'
CAS_USERNAME_FORMAT = lambda username: username.lower().strip()
CAS_LOGOUT_COMPLETELY = False

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

#####################
# Url configuration #
#####################

ROOT_URLCONF = '%s.urls' % SITE_NAME


######################
# WSGI configuration #
######################

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME


#############################
# Application configuration #
#############################

DJANGO_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    # 'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # 'django.contrib.admindocs',
    'django_cas',
]

THIRD_PARTY_APPS = [
    'django_extensions',
    'hijack',
    'compat',
    'hijack_admin',
    'django_summernote',
    'shibboleth',
]

LOCAL_APPS = [
    'immersionlyceens',
    'immersionlyceens.apps.core',
    'immersionlyceens.apps.immersion',
]


INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS


#########################
# Session configuration #
#########################

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

########################
# Passwords validation #
########################

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]


#####################
# Log configuration #
#####################

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(levelname)s %(asctime)s %(name)s:%(lineno)s %(message)s'},
        'django.server': {'()': 'django.utils.log.ServerFormatter', 'format': '[%(server_time)s] %(message)s',},
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse',},
        'require_debug_true': {'()': 'django.utils.log.RequireDebugTrue',},
    },
    'handlers': {
        'console': {'level': 'INFO', 'filters': ['require_debug_true'], 'class': 'logging.StreamHandler',},
        'django.server': {'level': 'INFO', 'class': 'logging.StreamHandler', 'formatter': 'django.server',},
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '',
            'maxBytes': 209715200,
            'backupCount': 3,
            'formatter': 'default',
        },
    },
    'loggers': {
        'django': {'handlers': ['console', 'mail_admins'], 'level': 'INFO',},
        'django.server': {'handlers': ['django.server'], 'level': 'INFO', 'propagate': False,},
        'immersionlyceens': {'handlers': ['mail_admins', 'file'], 'level': 'ERROR', 'propagate': True,},
    },
}

#################
# Django hijack #
#################
# Bootstrap notification bar that does not overlap with the default navbar.
HIJACK_USE_BOOTSTRAP = True
# Where admins are redirected to after hijacking a user
HIJACK_LOGIN_REDIRECT_URL = '/'
# Where admins are redirected to after releasing a user
HIJACK_LOGOUT_REDIRECT_URL = '/'  # Add to your settings file
CONTENT_TYPES = ['image', 'video']
# 2.5MB - 2621440
# 5MB - 5242880
# 10MB - 10485760
# 20MB - 20971520
# 50MB - 5242880
# 100MB - 104857600
# 250MB - 214958080
# 500MB - 429916160
MAX_UPLOAD_SIZE = "5242880"
HIJACK_ALLOW_GET_REQUESTS = True
HIJACK_REGISTER_ADMIN = False


#######################
# Admin page settings #
#######################

ADMIN_SITE_HEADER = _('Immersion')
ADMIN_SITE_TITLE = _('Immersion Admin Page')
ADMIN_SITE_INDEX_TITLE = _('Welcome to immersion administration page')

#################
# APIs settings #
#################

ACCOUNTS_CLIENT = 'immersionlyceens.libs.api.accounts.LdapAPI'

#####################
# LDAP API settings #
#####################

# Server
LDAP_API_HOST = ''
LDAP_API_PORT = ''
LDAP_API_DN = ''
LDAP_API_PASSWORD = ''
LDAP_API_BASE_DN = ''

# Filters
LDAP_API_ACCOUNTS_FILTER = ''

# Attributes
LDAP_API_SEARCH_ATTR = ''
LDAP_API_DISPLAY_ATTR = ''
LDAP_API_EMAIL_ATTR = ''
LDAP_API_EMAIL_USERNAME = ''
LDAP_API_LASTNAME_ATTR = ''
LDAP_API_FIRSTNAME_ATTR = ''

#######################
# SHIBBOLETH settings #
#######################

# Do not use : may not be unique accross institutions
# "HTTP_UID": (True, "username"),

SHIBBOLETH_ATTRIBUTE_MAP = {
    "HTTP_GIVENNAME": (True, "first_name"),
    "HTTP_SN": (True, "last_name"),
    "HTTP_REMOTE_USER": (True, "username"),
    "HTTP_MAIL": (True, "email"),
}

SHIBBOLETH_LOGOUT_URL = "/Shibboleth.sso/Logout"
SHIBBOLETH_LOGOUT_REDIRECT_URL = "/"

CREATE_UNKNOWN_USER = False

#######################
# Email configuration #
#######################

DEFAULT_FROM_EMAIL = 'support@unistra.fr'

# EMAIL_BACKEND choices :
#     - immersionlyceens.libs.mails.backends.EmailBackend
#     - immersionlyceens.libs.mails.backends.ConsoleBackend
#     - immersionlyceens.libs.mails.backends.FileBackend
EMAIL_BACKEND = 'immersionlyceens.libs.mails.backends.EmailBackend'
EMAIL_HOST = '127.0.0.1'
FROM_ADDR = 'no.reply@unistra.fr'

FORCE_EMAIL_ADDRESS = None


# Displaying apps order in ADMIN
ADMIN_APPS_ORDER = ['auth', 'core']

ADMIN_MODELS_ORDER = {
    'core': [
        'ImmersionUser',
        'UniversityYear',
        'HighSchool',
        'GeneralBachelorTeaching',
        'BachelorMention',
        'Campus',
        'Building',
        'Component',
        'TrainingDomain',
        'TrainingSubdomain',
        'Training',
        'CourseType',
        'PublicType',
        'CancelType',
        'Holiday',
        'Vacation',
        'Calendar',
        'MailTemplate',
    ]
}

# Define groups rights on others here ?
HAS_RIGHTS_ON_GROUP = {'SCUIO-IP': ['REF-CMP', 'REF-LYC',]}

####################
# Geo Api settings #
####################

USE_GEOAPI = True
GEOAPI_BASE_URL = "https://geo.api.gouv.fr"


####################
# Uploads settings #
####################

# Type of docs
# Use extension of files authorized !
CONTENT_TYPES = [
    'doc',
    'pdf',
    'xls',
    'ods',
    'odt',
    'docx',
]

# Max size
# 20mo for now !!!
MAX_UPLOAD_SIZE = "20971520"
# Values :
# 2.5MB - 2621440
# 5MB - 5242880
# 10MB - 10485760
# 20MB - 20971520
# 50MB - 5242880
# 100MB - 104857600
# 250MB - 214958080
# 500MB - 429916160

# Highschool students settings
USERNAME_PREFIX = "@EXTERNAL@_"
DESTRUCTION_DELAY = 5  # in days

# Some general settings default values
DEFAULT_NB_DAYS_SLOT_REMINDER = 4
DEFAULT_NB_DAYS_TEACHER_SLOT_REMINDER = 4
