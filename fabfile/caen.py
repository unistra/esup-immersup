"""
"""

import pydiploy
from fabric.api import env, execute, roles, task
from .map_settings import map_settings

@roles(['web', 'lb'])
def build_env():
    execute(pydiploy.prepare.build_env)

@task
def preprod_caen():
    """Define preprod stage for Caen instance"""
    env.roledefs = {
        'web': ['saas-caen-pprd-1.srv.unistra.fr', 'saas-caen-pprd-2.srv.unistra.fr'],
        'lb': ['saas-caen-pprd-1.srv.unistra.fr', 'saas-caen-pprd-2.srv.unistra.fr'],
        'shib': ['rp-shib3-pprd-1.srv.unistra.fr', 'rp-shib3-pprd-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_caen'
    env.backends = env.roledefs['web']
    env.server_name = 'immersup-pprd.unicaen.fr'
    env.short_server_name = 'immersup-pprd'
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
def prod_caen():
    """Define preprod stage for Caen instance"""
    env.roledefs = {
        'web': ['saas-caen-prod-1.srv.unistra.fr', 'saas-caen-prod-2.srv.unistra.fr'],
        'lb': ['saas-caen-prod-1.srv.unistra.fr', 'saas-caen-prod-2.srv.unistra.fr'],
        'shib': ['rp-shib3-prod-1.srv.unistra.fr', 'rp-shib3-prod-2.srv.unistra.fr'],  }

    # env.user = 'root'  # user for ssh
    env.application_name = 'immersup_caen'
    env.backends = env.roledefs['web']
    env.server_name = 'immersup.unicaen.fr'
    env.short_server_name = 'immersup'
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
