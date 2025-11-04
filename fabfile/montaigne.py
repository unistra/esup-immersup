"""
"""

import pydiploy
from fabric.api import env, execute, roles, task
from .map_settings import map_settings

@roles(['web', 'lb'])
def build_env():
    execute(pydiploy.prepare.build_env)

@task
def preprod_montaigne():
    """Define preprod stage for Bordeaux Montaigne instance"""
    env.roledefs = {
        'web': ['saas-bordeaux-montaigne-pprd-1.srv.unistra.fr', 'saas-bordeaux-montaigne-pprd-2.srv.unistra.fr'],
        'lb': ['saas-bordeaux-montaigne-pprd-1.srv.unistra.fr', 'saas-bordeaux-montaigne-pprd-2.srv.unistra.fr'],
        'shib': ['rp-shib3-pprd-1.srv.unistra.fr', 'rp-shib3-pprd-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_montaigne'
    env.backends = env.roledefs['web']
    env.server_name = 'bordeaux-montaigne.pprd.immersup.fr'
    env.short_server_name = 'immersion-dev'
    env.static_folder = '/site_media/'
    env.server_ip = '130.79.245.212'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'preprod'
    env.socket_port = '8001'
    env.map_settings = map_settings
    execute(build_env)


@task
def prod_montaigne():
    """Define preprod stage for Bordeaux Montaigne instance"""
    env.roledefs = {
        'web': ['saas-bordeaux-montaigne-prod-1.srv.unistra.fr', 'saas-bordeaux-montaigne-prod-2.srv.unistra.fr'],
        'lb': ['saas-bordeaux-montaigne-prod-1.srv.unistra.fr', 'saas-bordeaux-montaigne-prod-2.srv.unistra.fr'],
        'shib': ['rp-shib3-prod-1.srv.unistra.fr', 'rp-shib3-prod-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_montaigne'
    env.backends = env.roledefs['web']
    env.server_name = 'bordeaux-montaigne.immersup.fr'
    env.short_server_name = 'immersion'
    env.static_folder = '/site_media/'
    env.server_ip = '77.72.44.196'
    env.no_shared_sessions = False
    env.server_ssl_on = True
    env.path_to_cert = '/etc/ssl/certs/mega_wildcard.pem'
    env.path_to_cert_key = '/etc/ssl/private/mega_wildcard.key'
    env.goal = 'prod'
    env.socket_port = '8001'
    env.map_settings = map_settings
    execute(build_env)
