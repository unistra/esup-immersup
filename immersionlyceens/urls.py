from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from .apps.core import views as core_views
from .views import (
    accompanying, home, offer, offer_subdomain, procedure, serve_accompanying_document,
    serve_public_document,
)

from immersionlyceens.apps.immersion.views import shibbolethLogin

admin.autodiscover()


urlpatterns = [
    # Examples:
    path('', home, name='home'),
    path('shib/', shibbolethLogin, name='shibboleth_login'),
    path('secure', include('shibboleth.urls', namespace='shibboleth')), 
    path('accompanying', accompanying, name='accompanying'),
    path('accounts/', include('django_cas.urls', namespace='django_cas')),
    path('admin/', admin.site.urls),
    path('admin/holiday/import', core_views.import_holidays, name='import_holidays'),
    path('api/', include('immersionlyceens.libs.api.urls')),
    path('core/', include('immersionlyceens.apps.core.urls')),
    path(
        'dl/accdoc/<int:accompanying_document_id>',
        serve_accompanying_document,
        name='accompanying_document',
    ),
    path('dl/pubdoc/<int:public_document_id>', serve_public_document, name='public_document',),
    path('geoapi/', include('immersionlyceens.libs.geoapi.urls')),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('offer', offer, name='offer'),
    path('offer/<int:subdomain_id>', offer_subdomain, name='offer_subdomain'),
    path('procedure', procedure, name='procedure'),
    path('summernote/', include('django_summernote.urls')),
    path('immersion/', include('immersionlyceens.apps.immersion.urls', namespace='immersion')),
    path('charts/', include('immersionlyceens.apps.charts.urls', namespace='charts')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# debug toolbar for dev
if settings.DEBUG and 'debug_toolbar' in settings.INSTALLED_APPS:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]


admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.site_title = settings.ADMIN_SITE_TITLE
admin.site.index_title = settings.ADMIN_SITE_INDEX_TITLE
