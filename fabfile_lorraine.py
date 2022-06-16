# -*- coding: utf-8 -*-

"""
"""

from os.path import join

import pydiploy
from fabric.api import abort, env, execute, local, roles, task, warn_only
from fabric.context_managers import lcd
from pydiploy.decorators import do_verbose

# edit config here !
# TODO: check post_install & remove nginx useless stuff
# using apache + shibb mod for now !

env.remote_owner = 'django'  # remote server user
env.remote_group = 'di'  # remote server group

env.application_name = 'immersup'  # name of webapp
env.root_package_name = 'immersionlyceens'  # name of app in webapp

env.remote_home = '/home/django'  # remote home root
env.remote_python_version = '3.8'  # python version
env.remote_virtualenv_root = join(env.remote_home, '.virtualenvs')  # venv root
env.remote_virtualenv_dir = join(env.remote_virtualenv_root, env.application_name)  # venv for webapp dir
# git repository url
env.remote_repo_url = 'git@git.unistra.fr:di/immersionlyceens.git'
env.local_tmp_dir = '/tmp'  # tmp dir
env.remote_static_root = '/var/www/static/'  # root of static files
env.locale = 'fr_FR.UTF-8'  # locale to use on remote
env.timezone = 'Europe/Paris'  # timezone for remote
env.keep_releases = 2  # number of old releases to keep before cleaning
env.extra_goals = ['preprod']  # add extra goal(s) to defaults (test,dev,prod)
env.dipstrap_version = 'latest'
env.verbose_output = False  # True for verbose output
env.no_circus_web = True

# optional parameters

# env.dest_path = '' # if not set using env_local_tmp_dir
# env.excluded_files = ['pron.jpg'] # file(s) that rsync should exclude when deploying app
# env.extra_ppa_to_install = ['ppa:vincent-c/ponysay'] # extra ppa source(s) to use
# extra debian/ubuntu package(s) to install on remote :
env.extra_pkg_to_install = ['python3.8-dev', 'libxml2-dev', 'libxslt-dev', 'libffi-dev', 'postgresql-client', 
                            'postgresql-client-common', 'libcairo2-dev', 'libpango1.0-dev', 'libpq-dev']
# env.cfg_shared_files = ['config','/app/path/to/config/config_file'] # config files to be placed in shared config dir
# env.extra_symlink_dirs = ['mydir','/app/mydir'] # dirs to be symlinked in shared directory
# env.verbose = True # verbose display for pydiploy default value = True
# env.req_pydiploy_version = "0.9" # required pydiploy version for this fabfile
# env.no_config_test = False # avoid config checker if True
# env.maintenance_text = "" # add a customize maintenance text for maintenance page
# env.maintenance_title = "" # add a customize title for maintenance page
# env.oracle_client_version = '11.2'
# env.oracle_download_url = 'http://librepo.net/lib/oracle/'
# env.oracle_remote_dir = 'oracle_client'
# env.oracle_packages = ['instantclient-basic-linux-x86-64-11.2.0.2.0.zip',
#                        'instantclient-sdk-linux-x86-64-11.2.0.2.0.zip',
#                        'instantclient-sqlplus-linux-x86-64-11.2.0.2.0.zip']
#
# env.circus_package_name = 'https://github.com/morganbohn/circus/archive/master.zip'
# env.no_circus_web = True
# env.circus_backend = 'gevent' # name of circus backend to use

env.chaussette_backend = (
    'waitress'  # name of chaussette backend to use. You need to add this backend in the app requirement file.
)


# env.nginx_location_extra_directives = ['proxy_read_timeout 120'] # add directive(s) to nginx config file in location part
# env.nginx_start_confirmation = True # if True when nginx is not started
# needs confirmation to start it.


@task
def dev():
    """Define dev stage"""
    env.roledefs = {
        'web': ['192.168.1.2'],
        'lb': ['192.168.1.2'],
    }
    env.user = 'vagrant'
    env.backends = env.roledefs['web']
    env.server_name = 'immersionlyceens-dev.net'
    env.short_server_name = 'immersionlyceens-dev'
    env.static_folder = '/site_media/'
    env.server_ip = '192.168.1.2'
    env.no_shared_sessions = False
    env.server_ssl_on = False
    env.goal = 'dev'
    env.socket_port = '8001'
    env.map_settings = {}
    execute(build_env)


@task
def preprod():
    """Define preprod stage"""
    env.roledefs = {
        'web': ['saas-lorraine-pprd-1.srv.unistra.fr', 'saas-lorraine-pprd-2.srv.unistra.fr'],
        'lb': ['saas-lorraine-pprd-1.srv.unistra.fr', 'saas-lorraine-pprd-2.srv.unistra.fr'],
        'shib': ['rp-shib3-pprd-1.srv.unistra.fr', 'rp-shib3-pprd-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh

    env.backends = env.roledefs['web']
    env.server_name = 'immersup-pprd.univ-lorraine.fr'
    env.short_server_name = 'immersup-pprd'
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
        'base_files_dir': "BASE_FILES_DIR",
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
    }
    execute(build_env)


@task
def prod():
    """Define prod stage"""
    env.roledefs = {
        # 'web': ['django-w3.u-strasbg.fr', 'django-w4.u-strasbg.fr'],
        'web': ['django-w7.di.unistra.fr', 'django-w8.di.unistra.fr'],
        'lb': ['rp-dip-public-m.di.unistra.fr', 'rp-dip-public-s.di.unistra.fr'],
        'shib': ['root@rp-apache-shib2-m.di.unistra.fr', 'root@rp-apache-shib2-s.di.unistra.fr']
    }

    # env.user = 'root'  # user for ssh
    env.backends = env.roledefs['web']
    env.server_name = 'immersup.unistra.fr'
    env.short_server_name = 'immersup'
    env.static_folder = '/site_media/'
    env.server_ip = '130.79.245.214'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'prod'
    env.socket_port = '8010'
    env.map_settings = {
        'default_db_host': "DATABASES['default']['HOST']",
        'default_db_user': "DATABASES['default']['USER']",
        'default_db_password': "DATABASES['default']['PASSWORD']",
        'default_db_name': "DATABASES['default']['NAME']",
        'secret_key': "SECRET_KEY",
        'cas_redirect_url': "CAS_REDIRECT_URL",
        'base_files_dir': "BASE_FILES_DIR",
        'release': "RELEASE",
        's3_access_key': "AWS_ACCESS_KEY_ID",
        's3_secret_key': "AWS_SECRET_ACCESS_KEY",
        's3_bucket': "AWS_STORAGE_BUCKET_NAME",
        's3_endpoint': "AWS_S3_ENDPOINT_URL",
        'email_host': "EMAIL_HOST",
        'email_port': "EMAIL_PORT",
        'email_use_tls': "EMAIL_USE_TLS",
        'email_host_user': "EMAIL_HOST_USER",
        'email_host_password': "EMAIL_HOST_PASSWORD",
        'force_email_address': "FORCE_EMAIL_ADDRESS",
        'default_from_email': "DEFAULT_FROM_EMAIL",
        # TODO: should be used later
        # 'matomo_url': "MATOMO_URL",
        # 'matomo_site_id': "MATOMO_SITE_ID"
    }
    execute(build_env)


# dont touch after that point if you don't know what you are doing !


@task
def tag(version_number):
    """ Set the version to deploy to `version_number`. """
    execute(pydiploy.prepare.tag, version=version_number)


@roles(['web', 'lb'])
def build_env():
    execute(pydiploy.prepare.build_env)


@task
def pre_install():
    """Pre install of backend & frontend"""
    execute(pre_install_backend)
    execute(pre_install_frontend)


@roles('web')
@task
def pre_install_backend():
    """Setup server for backend"""
    execute(pydiploy.django.pre_install_backend, commands='/usr/bin/rsync')


@roles('lb')
@task
def pre_install_frontend():
    """Setup server for frontend"""
    execute(pydiploy.django.pre_install_frontend)


@task
def deploy(update_pkg=False):
    """Deploy code on server"""
    execute(deploy_backend, update_pkg)
    execute(deploy_frontend)
    # Uncomment this to use sentry when deploying new version
    # execute(declare_release_to_sentry)


@roles('web')
@task
def deploy_backend(update_pkg=False):
    """Deploy code on server"""
    execute(pydiploy.django.deploy_backend, update_pkg)


@roles('lb', 'shib')
@task
def deploy_frontend():
    """Deploy static files on load balancer"""
    execute(pydiploy.django.deploy_frontend)


@roles('web')
@task
def rollback():
    """Rollback code (current-1 release)"""
    execute(pydiploy.django.rollback)


@task
def post_install():
    """post install for backend & frontend"""
    execute(post_install_backend)
    execute(post_install_frontend)


@roles('web')
@task
def post_install_backend():
    """Post installation of backend"""
    execute(pydiploy.django.post_install_backend)


@roles('lb')
@task
def post_install_frontend():
    """Post installation of frontend"""
    execute(pydiploy.django.post_install_frontend)


@roles('web')
@task
def install_postgres(user=None, dbname=None, password=None):
    """Install Postgres on remote"""
    execute(pydiploy.django.install_postgres_server, user=user, dbname=dbname, password=password)


@task
def reload():
    """Reload backend & frontend"""
    execute(reload_frontend)
    execute(reload_backend)


@roles('lb')
@task
def reload_frontend():
    execute(pydiploy.django.reload_frontend)


@roles('web')
@task
def reload_backend():
    execute(pydiploy.django.reload_backend)


@roles('lb')
@task
def set_down():
    """ Set app to maintenance mode """
    execute(pydiploy.django.set_app_down)


@roles('lb')
@task
def set_up():
    """ Set app to up mode """
    execute(pydiploy.django.set_app_up)


@roles('web')
@task
def custom_manage_cmd(cmd):
    """ Execute custom command in manage.py """
    execute(pydiploy.django.custom_manage_command, cmd)


##########
# Sentry #
##########

@task
def declare_release_to_sentry():
    execute(declare_release)


@do_verbose
def env_setup():
    local_repo = local("pwd", capture=True)
    distant_repo = local("git config --get remote.origin.url", capture=True)
    temp_dir = local("mktemp -d", capture=True)
    working_dir = join(temp_dir, "git-clone")
    project_version = ""

    # First we git clone the local repo in the local tmp dir
    with lcd(temp_dir):
        print("Cloning local repo in {}".format(local("pwd", capture=True)))
        local("git clone {} {}".format(local_repo, working_dir))
    with lcd(working_dir):

        # As a result of the local git clone, the origin of the cloned repo is the local repo
        # So we reset it to be the distant repo
        print("Setting origin in the temp repo to be {}".format(distant_repo))
        local("git remote remove origin")
        local("git remote add origin {}".format(distant_repo))
        project_version = local("git describe --tags", capture=True)
        print("Getting project version to declare to Sentry ({})".format(project_version))

    return project_version


@ do_verbose
def declare_release():
    project_version = env_setup()

    # Create a release
    print("Declaring new release to Sentry")
    with warn_only():
        c = local("sentry-cli releases new -p {} {}".format(
            'immersion',
            project_version
        ), capture=True)
        if c.failed:
            abort("Sentry-cli not installed or improper configuration")

        else:
            return c

    # Associate commits with the release
    print("Associating commits with new release for Sentry")
    local("sentry-cli releases set-commits --auto {}".format(project_version))

    # Declare deployment
    print("Declaring new deployment to Sentry")
    local("sentry-cli releases deploys {} new -e {}".format(
        project_version,
        env.goal
    ))
