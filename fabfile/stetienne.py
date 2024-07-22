"""
"""

import pydiploy
from fabric.api import env, execute, roles, task
# from . import build_env

@roles(['web', 'lb'])
def build_env():
    execute(pydiploy.prepare.build_env)

@task
def preprod_stetienne():
    """Define preprod stage for St Etienne instance"""
    env.roledefs = {
        'web': ['saas-stetienne-pprd-1.srv.unistra.fr', 'saas-stetienne-pprd-2.srv.unistra.fr'],
        'lb': ['saas-stetienne-pprd-1.srv.unistra.fr', 'saas-stetienne-pprd-2.srv.unistra.fr'],
        'shib': ['rp-shib3-pprd-1.srv.unistra.fr', 'rp-shib3-pprd-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_stetienne'
    env.backends = env.roledefs['web']
    env.server_name = 'immersup-pp.univ-st-etienne.fr'
    env.short_server_name = 'immersup-pp'
    env.static_folder = '/site_media/'
    env.server_ip = '130.79.245.212'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'preprod'
    env.socket_port = '8001'
    env.map_settings = {
        'default_db_host': "DATABASES['default']['HOST']",
        'default_db_user': "DATABASES['default']['USER']",
        'default_db_password': "DATABASES['default']['PASSWORD']",
        'default_db_name': "DATABASES['default']['NAME']",
        'secret_key': "SECRET_KEY",
        'cas_redirect_url': "CAS_REDIRECT_URL",
        'release': "RELEASE",
        's3_access_key': "AWS_ACCESS_KEY_ID",
        's3_secret_key': "AWS_SECRET_ACCESS_KEY",
        's3_bucket': "AWS_STORAGE_BUCKET_NAME",
        's3_endpoint': "AWS_S3_ENDPOINT_URL",
        'matomo_url': "MATOMO_URL",
        'matomo_site_id': "MATOMO_SITE_ID",
        'use_unistra_theme': "UNISTRA",
        'email_host': "EMAIL_HOST",
        'email_port': "EMAIL_PORT",
        'email_use_tls': "EMAIL_USE_TLS",
        'email_host_user': "EMAIL_HOST_USER",
        'email_host_password': "EMAIL_HOST_PASSWORD",
        'force_email_address': "FORCE_EMAIL_ADDRESS",
        'default_from_email': "DEFAULT_FROM_EMAIL",
        'extra_locale_path': "EXTRA_LOCALE_PATH",
        'csrf_trusted_origins': f"https://{env.server_name}",
    }
    execute(build_env)


@task
def prod_stetienne():
    """Define preprod stage for St-Etienne instance"""
    env.roledefs = {
        'web': ['saas-stetienne-prod-1.srv.unistra.fr', 'saas-stetienne-prod-2.srv.unistra.fr'],
        'lb': ['saas-stetienne-prod-1.srv.unistra.fr', 'saas-stetienne-prod-2.srv.unistra.fr'],
        'shib': ['rp-shib3-prod-1.srv.unistra.fr', 'rp-shib3-prod-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_stetienne'
    env.backends = env.roledefs['web']
    env.server_name = 'immersup.univ-st-etienne.fr'
    env.short_server_name = 'immersup'
    env.static_folder = '/site_media/'
    env.server_ip = '77.72.44.196'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'prod'
    env.socket_port = '8001'
    env.map_settings = {
        'default_db_host': "DATABASES['default']['HOST']",
        'default_db_user': "DATABASES['default']['USER']",
        'default_db_password': "DATABASES['default']['PASSWORD']",
        'default_db_name': "DATABASES['default']['NAME']",
        'secret_key': "SECRET_KEY",
        'cas_redirect_url': "CAS_REDIRECT_URL",
        'release': "RELEASE",
        's3_access_key': "AWS_ACCESS_KEY_ID",
        's3_secret_key': "AWS_SECRET_ACCESS_KEY",
        's3_bucket': "AWS_STORAGE_BUCKET_NAME",
        's3_endpoint': "AWS_S3_ENDPOINT_URL",
        'matomo_url': "MATOMO_URL",
        'matomo_site_id': "MATOMO_SITE_ID",
        'use_unistra_theme': "UNISTRA",
        'email_host': "EMAIL_HOST",
        'email_port': "EMAIL_PORT",
        'email_use_tls': "EMAIL_USE_TLS",
        'email_host_user': "EMAIL_HOST_USER",
        'email_host_password': "EMAIL_HOST_PASSWORD",
        'force_email_address': "FORCE_EMAIL_ADDRESS",
        'default_from_email': "DEFAULT_FROM_EMAIL",
        'extra_locale_path': "EXTRA_LOCALE_PATH",
        'csrf_trusted_origins': f"https://{env.server_name}",
    }
    execute(build_env)
