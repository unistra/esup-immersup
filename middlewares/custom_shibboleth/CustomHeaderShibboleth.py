from django.conf import settings
from django.contrib.auth.middleware import RemoteUserMiddleware
from shibboleth.middleware import ShibbolethRemoteUserMiddleware

class CustomHeaderMiddleware(ShibbolethRemoteUserMiddleware):
    header = getattr(settings, "SHIBBOLETH_REMOTE_USER_ATTR", ShibbolethRemoteUserMiddleware.header)
