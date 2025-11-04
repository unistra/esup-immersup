# -*- coding: utf-8 -*-

"""
"""

from os.path import join

import pydiploy
from fabric.api import abort, env, execute, local, roles, task, warn_only
from fabric.context_managers import lcd
from pydiploy.decorators import do_verbose

from angers import preprod_angers, prod_angers
from bordeaux import preprod_bordeaux, prod_bordeaux
from caen import preprod_caen, prod_caen
from lemans import preprod_lemans, prod_lemans
from lorraine import preprod_lorraine, prod_lorraine
from lyon import preprod_lyon, prod_lyon
from montaigne import preprod_montaigne, prod_montaigne
from pau import preprod_pau, prod_pau
from reims import preprod_reims, prod_reims
from rouen import preprod_rouen, prod_rouen
from savoie import preprod_savoie, prod_savoie
from stetienne import preprod_stetienne, prod_stetienne

from map_settings import map_settings

# edit config here !
# TODO: check post_install & remove nginx useless stuff
# using apache + shibb mod for now !

env.remote_owner = 'django'  # remote server user
env.remote_group = 'di'  # remote server group

env.application_name = 'immersup'  # name of webapp
env.root_package_name = 'immersionlyceens'  # name of app in webapp

env.remote_home = '/home/django'  # remote home root
env.remote_python_version = '3.12'  # python version
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

# Circus / uwsgi
env.enable_circus = True # Default: True
env.enable_uwsgi = False # Default: False

# Defaults - override in tasks when needed
env.remote_uwsgi_emperor_service_name = "uwsgi-emperor"
env.remote_uwsgi_emperor_path = "/etc/uwsgi-emperor"
env.remote_uwsgi_vassal_plugins = "python3,logfile"
env.remote_uwsgi_emperor_owner = "root"
env.remote_uwsgi_emperor_group = "root"
env.remote_uwsgi_vassal_owner = "www-data"
env.remote_uwsgi_vassal_group = "di"

# optional parameters

# env.dest_path = '' # if not set using env_local_tmp_dir
# env.excluded_files = ['pron.jpg'] # file(s) that rsync should exclude when deploying app
# env.extra_ppa_to_install = ['ppa:vincent-c/ponysay'] # extra ppa source(s) to use

# extra debian/ubuntu package(s) to install on remote
env.extra_pkg_to_install = [
    'python3.12-dev', 'libxml2-dev', 'libxslt-dev', 'libffi-dev', 'postgresql-client',
    'postgresql-client-common', 'libcairo2-dev', 'libpango1.0-dev', 'libpq-dev', 'libmagic1',
    'libtk8.6', 'python3.12-tk'
]

# env.cfg_shared_files = ['config','/app/path/to/config/config_file'] # config files to be placed in shared config dir
# env.extra_symlink_dirs = ['mydir','/app/mydir'] # dirs to be symlinked in shared directory

env.extra_symlink_dirs = ['config', ]

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
def test():
    """Define test stage"""
    env.roledefs = {
        'web': ['django-test2.di.unistra.fr'],
        'lb': ['django-test2.di.unistra.fr'],
        'shib': ['rp-apache-shib2-m-pprd.di.unistra.fr', 'rp-apache-shib2-s-pprd.di.unistra.fr'],
    }

    # Remove this for test env
    map_settings.pop('secret_key', None)

    env.enable_circus = False
    env.enable_uwsgi = True
    
    # uwsgi settings
    env.remote_uwsgi_emperor_service_name = "emperor.uwsgi.python3.12"
    env.remote_uwsgi_emperor_path = "/etc/uwsgi"
    env.remote_uwsgi_emperor_owner = "root"
    env.remote_uwsgi_emperor_group = "root"

    env.remote_uwsgi_vassal_owner = "django"
    env.remote_uwsgi_vassal_group = "di"


    # env.user = 'root'  # user for ssh
    env.backends = ['0.0.0.0']
    env.server_name = 'immersup-test.app.unistra.fr'
    env.short_server_name = 'immersup-test'
    env.static_folder = '/site_media/'
    env.server_ip = ''
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'test'
    env.socket_port = '8042'
    env.socket_host = '127.0.0.1'
    env.map_settings = map_settings
    env.extra_symlink_dirs = ['media']
    execute(build_env)

@task
def preprod():
    """Define preprod stage"""
    env.roledefs = {
        'web': ['django-pprd-w3.di.unistra.fr', 'django-pprd-w4.di.unistra.fr'],
        'lb': ['rp-dip-pprd-public.di.unistra.fr'],
        'shib': ['rp-shib3-pprd-1.srv.unistra.fr', 'rp-shib3-pprd-2.srv.unistra.fr'],
    }

    # env.user = 'root'  # user for ssh
    env.backends = env.roledefs['web']
    env.server_name = 'immersup-pprd.app.unistra.fr'
    env.short_server_name = 'immersup-pprd'
    env.static_folder = '/site_media/'
    env.server_ip = '77.72.45.206'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'preprod'
    env.socket_port = '8044'
    env.map_settings = map_settings
    execute(build_env)


@task
def prod():
    """Define prod stage"""
    env.roledefs = {
        # 'web': ['django-w3.u-strasbg.fr', 'django-w4.u-strasbg.fr'],
        'web': ['django-w7.di.unistra.fr', 'django-w8.di.unistra.fr'],
        'lb': ['rp-dip-public-m.di.unistra.fr', 'rp-dip-public-s.di.unistra.fr'],
        'shib': ['rp-apache-shib2-m.di.unistra.fr', 'rp-apache-shib2-s.di.unistra.fr']
    }

    # env.user = 'root'  # user for ssh
    env.backends = env.roledefs['web']
    env.server_name = 'immersion.projet-noria.fr'
    env.short_server_name = 'immersup'
    env.static_folder = '/site_media/'
    env.server_ip = '130.79.245.214'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/immersion.projet-noria.fr.crt'
    env.path_to_cert_key = '/etc/ssl/private/immersion.projet-noria.fr.key'
    env.goal = 'prod'
    env.socket_port = '8012'
    env.map_settings = map_settings
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


@roles("web")
@task
def update_python_version():
    """Update python version according to remote_python_version"""
    execute(pydiploy.django.update_python_version)


@task
def deploy_all_preprod():
    preprod()
    deploy()
    preprod_bordeaux()
    deploy()
    preprod_caen()
    deploy()
    preprod_lorraine()
    deploy()
    preprod_stetienne()
    deploy()
    preprod_pau()
    deploy()
    preprod_reims()
    deploy()
    preprod_lemans()
    deploy()
    preprod_rouen()
    deploy()
    preprod_savoie()
    deploy()

@task
def deploy_all_prod():
    prod()
    deploy()
    prod_bordeaux()
    deploy()
    prod_caen()
    deploy()
    prod_lorraine()
    deploy()
    prod_stetienne()
    deploy()
    prod_pau()
    deploy()
    prod_reims()
    deploy()
    prod_rouen()
    deploy()


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
