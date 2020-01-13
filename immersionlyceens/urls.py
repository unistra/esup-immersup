from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from .views import home

admin.autodiscover()

urlpatterns = [
    # Examples:
    path('', home, name='home'),
    # path('app/', include('apps.app.urls')),

    path('admin/', admin.site.urls),
    path('accounts/', include('django_cas.urls', namespace='django_cas')),
    path('hijack/', include('hijack.urls', namespace='hijack')),
]

# debug toolbar for dev
if settings.DEBUG and 'debug_toolbar'in settings.INSTALLED_APPS:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
