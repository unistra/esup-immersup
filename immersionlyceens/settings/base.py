import os
import re
import csv
from os.path import abspath, basename, dirname, join, normpath

from django.utils.translation import gettext_lazy as _

from ckeditor.configs import DEFAULT_CONFIG

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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# PostgreSQL unaccent extension
POSTGRESQL_ADD_UNACCENT_EXTENSION = True # For migration file
POSTGRESQL_HAS_UNACCENT_EXTENSION = True # For queries


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
        'DIRS': [join(DJANGO_ROOT, 'templates')],
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
                'immersionlyceens.apps.context_processors.establishments',
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
    'middlewares.custom_shibboleth.CustomHeaderShibboleth.CustomHeaderMiddleware',
    'middlewares.charter_management.ImmersionCharterManagement.ImmersionCharterManagement',
    'middlewares.email_check.EmailCheck.EmailCheck',
    'hijack.middleware.HijackUserMiddleware',

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
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

#####################
#       CAS         #
#####################

# By default, do not activate CAS features, Shibboleth is prefered
# Use CAS only in dev instances where Shibboleth is not available
USE_CAS = False

CAS_SERVER_URL = 'https://cas.unistra.fr:443/cas/'
CAS_LOGOUT_REQUEST_ALLOWED = ('cas1.di.unistra.fr', 'cas2.di.unistra.fr')
CAS_USER_CREATION = False
CAS_IGNORE_REFERER = True
CAS_REDIRECT_URL = '/'
CAS_USERNAME_FORMAT = lambda username: username.lower().strip()
CAS_RETRY_LOGIN = True

# CAS_LOGOUT_COMPLETELY = True
CAS_FORCE_SSL_SERVICE_URL = True
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
    'django.contrib.postgres',
    'django_cas',
    # 'django.contrib.admindocs',
]

THIRD_PARTY_APPS = [
    'django_extensions',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'hijack',
    'hijack.contrib.admin',
    'ckeditor',
    'django_json_widget',
    'django_admin_listfilter_dropdown',
    'adminsortable2',
    'shibboleth',
    'django_countries',
    'drf_spectacular',
]

LOCAL_APPS = [
    'immersionlyceens',
    'immersionlyceens.apps.core',
    'immersionlyceens.apps.immersion',
    'immersionlyceens.apps.charts',
    'immersionlyceens.apps.user',
    'immersionlyceens.apps.api',
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
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


#####################
# Log configuration #
#####################

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {'format': '%(levelname)s %(asctime)s %(name)s:%(lineno)s %(message)s'},
        'django.server': {'()': 'django.utils.log.ServerFormatter', 'format': '[%(server_time)s] %(message)s', },
    },
    'filters': {
        'require_debug_false': {'()': 'django.utils.log.RequireDebugFalse', },
        'require_debug_true': {'()': 'django.utils.log.RequireDebugTrue', },
    },
    'handlers': {
        'console': {'level': 'INFO', 'filters': ['require_debug_true'], 'class': 'logging.StreamHandler', },
        'django.server': {'level': 'INFO', 'class': 'logging.StreamHandler', 'formatter': 'django.server', },
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
        'django': {'handlers': ['console', 'mail_admins'], 'level': 'INFO', },
        'django.server': {'handlers': ['django.server'], 'level': 'INFO', 'propagate': False, },
        'immersionlyceens': {'handlers': ['mail_admins', 'file'], 'level': 'ERROR', 'propagate': True, },
        'default': {'handlers': ['file'], 'level': 'INFO', 'propagate': True, },
    },
}

######################################
# django-restframework configuration #
######################################

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        "rest_framework.permissions.IsAuthenticated",
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'EXCEPTION_HANDLER': 'rest_framework_custom_exceptions.exceptions.simple_error_handler',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'ImmerSup API',
    'DESCRIPTION': 'High school students immersions',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}


#######################
# Admin page settings #
#######################

ADMIN_SITE_HEADER = "ImmerSup %s" % __import__('immersionlyceens').get_version()
ADMIN_SITE_TITLE = _('ImmerSup Admin Page')
ADMIN_SITE_INDEX_TITLE = _('Welcome to ImmerSup administration page')

#################
# Django hijack #
#################
# HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_only"
# HIJACK_PERMISSION_CHECK = "hijack.permissions.superusers_and_staff"
HIJACK_PERMISSION_CHECK = "immersionlyceens.permissions.hijack_permissions"


#################
# APIs settings #
#################

# Feel free to implement your own accounts search functions and
# enter your plugin name here :)

ACCOUNTS_PLUGINS = {
    'LDAP': 'immersionlyceens.libs.api.accounts.ldap',
    'REST': 'immersionlyceens.libs.api.accounts.rest'
}

AVAILABLE_ACCOUNTS_PLUGINS = (
    ('LDAP', 'LDAP'),
    ('REST', 'REST'),
)

#######################
# SHIBBOLETH settings #
#######################

# Do not use : may not be unique accross institutions
# "HTTP_UID": (True, "username"),
# Instead, http_remote_user should be the email of the user

SHIBBOLETH_REMOTE_USER_ATTR = "HTTP_REMOTE_USER"

# Old : "HTTP_REMOTE_USER": (False, "username"),

SHIBBOLETH_ATTRIBUTE_MAP = {
    "HTTP_REMOTE_USER": (False, "username"),
    "HTTP_GIVENNAME": (False, "first_name"),
    "HTTP_SN": (False, "last_name"),
    "HTTP_MAIL": (False, "email"),
    "HTTP_SUPANNETABLISSEMENT": (False, "uai_code"),
    "HTTP_AFFILIATION": (False, "affiliation"),
    "HTTP_UNSCOPED_AFFILIATION": (False, "unscoped_affiliation"),
    "HTTP_PRIMARY_AFFILIATION": (False, "primary_affiliation"),
    "HTTP_SUPANNETUETAPE": (False, 'etu_stage'),
    "HTTP_SUPANNOIDCDATEDENAISSANCE": (False, 'birth_date'),
}

SHIBBOLETH_LOGOUT_URL = "/Shibboleth.sso/Logout?return=%s"
SHIBBOLETH_LOGOUT_REDIRECT_URL = "/"
SHIBBOLETH_UNQUOTE_ATTRIBUTES = True

CREATE_UNKNOWN_USER = False

# Federations URLs
EDUCONNECT_LOGIN_URL = ""
EDUCONNECT_LOGOUT_URL = ""
AGENT_FEDERATION_LOGIN_URL = ""
AGENT_FEDERATION_LOGOUT_URL = ""

EDUCONNECT_URLS = [
    "educonnect.education.gouv.fr",
    "pr4.educonnect.phm.education.gouv.fr"
]

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
EMAIL_USE_TLS = False
EMAIL_SSL_ON_CONNECT = False
EMAIL_PORT = 25
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

FROM_ADDR = 'no.reply@unistra.fr'

FORCE_EMAIL_ADDRESS = None


# Displaying apps order in ADMIN
# Use virtual app names to regroup models
ADMIN_APPS_ORDER = [
    'auth', 'utilisateurs', 'calendrier', 'etablissements', 'formations', 'lieux', 'etudes', 'docs',
    'evaluations', 'configuration', 'user', 'authtoken'
]

ADMIN_APPS_MAPPING = {
    'utilisateurs': {'app': 'core', 'name': 'Utilisateurs'},
    'calendrier': {'app': 'core', 'name': 'Calendrier'},
    'etablissements': {'app': 'core', 'name': 'Établissements'},
    'formations': {'app': 'core', 'name': 'Formations et évènements'},
    'lieux': {'app': 'core', 'name': 'Lieux'},
    'etudes': {'app': 'core', 'name': 'Études'},
    'docs': {'app': 'core', 'name': 'Messages et documents'},
    'evaluations': {'app': 'core', 'name': 'Évaluations'},
    'configuration': {'app': 'core', 'name': 'Autres paramètres'},
}

ADMIN_MODELS_ORDER = {
    'utilisateurs': [
        'ImmersionUser',
    ],
    'calendrier': [
        'UniversityYear',
        'Vacation',
        'Holiday',
        'Period',
        'AnnualStatistics',
    ],
    'etablissements': [
        'Establishment',
        'HighSchool',
        'Structure',
    ],
    'formations': [
        'TrainingDomain',
        'TrainingSubdomain',
        'Training',
        'CourseType',
        'CancelType',
        'OffOfferEventType',
    ],
    'lieux': [
        'Campus',
        'Building',
    ],
    'etudes': [
        'BachelorType',
        'GeneralBachelorTeaching',
        'BachelorMention',
        'HighSchoolLevel',
        'MefStat',
        'PostBachelorLevel',
        'StudentLevel',
        'VisitorType',
    ],
    'docs': [
        'MailTemplate',
        'FaqEntry',
        'PublicDocument',
        'PublicType',
        'InformationText',
        'AccompanyingDocument',
        'AttestationDocument',
        'CertificateLogo',
        'CertificateSignature',
    ],
    'evaluations': [
        'EvaluationType',
        'EvaluationFormLink',
    ],
    'configuration': [
        'GeneralSettings',
        'Profile',
        'ScheduledTask',
        'CustomThemeFile',
        'ScheduledTask',
        'ScheduledTaskLog',
        'History',
    ],
    'user': [
        'Student',
        'HighSchoolStudent',
        'Visitor',
        'Speaker',
        'Operator',
        'MasterEstablishmentManager',
        'EstablishmentManager',
        'StructureManager',
        'StructureConsultant',
        'HighSchoolManager',
        'LegalDepartmentStaff',
        'UserGroup'
    ]
}

# Define groups rights on others
# DO NOT EDIT
HAS_RIGHTS_ON_GROUP = {
    'REF-TEC': ['REF-TEC', 'REF-ETAB-MAITRE', 'REF-ETAB', 'REF-STR', 'REF-LYC', 'SRV-JUR', 'INTER', 'LYC', 'VIS', 'ETU', 'CONS-STR'],
    'REF-ETAB-MAITRE': ['REF-ETAB', 'REF-STR', 'REF-LYC', 'SRV-JUR', 'INTER', 'CONS-STR'],
    'REF-ETAB': ['REF-STR', 'SRV-JUR', 'INTER', 'CONS-STR'],
    'REF-LYC': ['INTER']
}


############
# CKEDITOR #
############
X_FRAME_OPTIONS = 'SAMEORIGIN'
CUSTOM_TOOLBAR = [
    {
        "name": "document",
        "items": [
            "Styles",
            "Format",
            "Font",
            "Bold",
            "Italic",
            "Underline",
            "Strike",
            "-",
            "TextColor",
            "BGColor",
            "-",
            "JustifyLeft",
            "JustifyCenter",
            "JustifyRight",
            "JustifyBlock",
        ],
    },
    {
        "name": "widgets",
        "items": [
            "Undo",
            "Redo",
            "-",
            "NumberedList",
            "BulletedList",
            "-",
            "Outdent",
            "Indent",
            "-",
            "Link",
            "Unlink",
            "-",
            "CodeSnippet",
            "Table",
            "HorizontalRule",
            "SpecialChar",
            "-",
            "Blockquote",
            "-",
            "Maximize",
        ],
    },
]

"""
CKEDITOR_CONFIGS = {
    "default": {
        "skin": "moono-lisa",
        "toolbar": CUSTOM_TOOLBAR,
        "toolbarGroups": None,
        "extraPlugins": ",".join(
            [
                'codesnippet',
            ]
        ),
        "removePlugins": ",".join(['image', 'uploadimage', 'uploadwidget', 'elementspath']),
        "codeSnippet_theme": "xcode",
        'height': '100%',
        'width': '100%',
    },
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
            ],
        ],
        [
            'font',
            [
                'fontsize',
                'forecolor',
                'paragraph',
            ],
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
            ['link', 'table', 'hr'],
        ],
        [
            'view',
            ['codeview', 'undo', 'redo', 'fullscreen'],
        ],
    ],
    'popover': {
        'link': ['link', ['linkDialogShow', 'unlink']],
        'table': [
            ['add', ['addRowDown', 'addRowUp', 'addColLeft', 'addColRight']],
            ['delete', ['deleteRow', 'deleteCol', 'deleteTable']],
        ],
    },
}
"""

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono',
        # 'skin': 'office2013',
        'toolbar_Basic': [
            ['Source', '-', 'Bold', 'Italic']
        ],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'clipboard', 'items': ['Undo', 'Redo']},
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', '-',
                       'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl']},
            {'name': 'links', 'items': ['Link', 'Unlink']},
            '/',
            {'name': 'insert',
             'items': ['Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Preview', 'Maximize', 'ShowBlocks']},
            {'name': 'about', 'items': ['About']},
        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        # 'toolbarGroups': [{ 'name': 'document', 'groups': [ 'mode', 'document', 'doctools' ] }],
        # 'height': 291,
        # 'width': '100%',
        'height': 'full',
        'width': 'full',
        # 'filebrowserWindowHeight': 725,
        # 'filebrowserWindowWidth': 940,
        # 'toolbarCanCollapse': True,
        # 'mathJaxLib': '//cdn.mathjax.org/mathjax/2.2-latest/MathJax.js?config=TeX-AMS_HTML',
        'tabSpaces': 4,
        'extraPlugins': ','.join([
            # 'uploadimage', # the upload image feature
            # your extra plugins here
            'div',
            'autolink',
            'autoembed',
            'embedsemantic',
            'autogrow',
            # 'devtools',
            'widget',
            'lineutils',
            'clipboard',
            'dialog',
            'dialogui',
            # 'elementspath'
        ]),
        "removePlugins": ",".join(['resize', 'image', 'uploadimage', 'uploadwidget', 'elementspath']),
    }
}


CKEDITOR_UPLOAD_PATH = "ckeditor_uploads/"

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
    'xlsx',
]

MIME_TYPES = [
    "application/msword",
    "application/pdf",
    "application/vnd.ms-excel",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
# USERNAME_PREFIX = "@EXTERNAL@_"
DESTRUCTION_DELAY = 5  # in days

# Some general settings default values
DEFAULT_NB_DAYS_SLOT_REMINDER = 4
DEFAULT_NB_DAYS_SPEAKER_SLOT_REMINDER = 4
DEFAULT_NB_WEEKS_STRUCTURES_SLOT_REMINDER = 1

# Opendata
# This should be a stable URL according to this site :
# https://www.data.gouv.fr/fr/datasets/etablissements-denseignement-superieur-2
# INSTITUTES_URL = "https://api.opendata.onisep.fr/downloads/57da952417293/57da952417293.json"
INSTITUTES_URL = (
    "https://data.enseignementsup-recherche.gouv.fr/api/records/1.0/search/?"
    + "dataset=fr-esr-principaux-etablissements-enseignement-superieur&facet=uai&facet=type_d_etablissement"
    + "&facet=com_nom&facet=dep_nom&facet=aca_nom&facet=reg_nom&facet=pays_etranger_acheminement"
    + "&rows=%s&start=%s"
)  # don't forget to add rows and start values in requests for pagination


# Notifications display time (milliseconds)
MESSAGES_TIMEOUT = 8000

# Ignored queries for 404 error
IGNORABLE_404_URLS = [
    re.compile(r'^/apple-touch-icon.*\.png$'),
    re.compile(r'^/favicon\.ico$'),
    re.compile(r'^/robots\.txt$'),
]

# django countries settings
COUNTRIES_FIRST = ['FR',]

# Expiration of S3 url very looooooooooooooong :)
AWS_QUERYSTRING_EXPIRE = 999999999

########################
# CSV exports settings #
########################
# TODO: move to general settings ?
# Used to generate csv compliant with ms-excel
CSV_OPTIONS = {'delimiter': ';', 'quotechar': '"', 'quoting': csv.QUOTE_ALL, 'dialect': csv.excel}


###########################
#  SEARCH PLUGIN FOR UAI  #
###########################
# Configure this on deployment since it will contain API Key
UAI_API_URL = ""
UAI_API_AUTH_HEADER = ""
