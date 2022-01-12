from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from immersionlyceens.apps.immersion.views import shibbolethLogin

from .apps.core import views as core_views
from .views import (
    accompanying, home, offer, offer_off_offer_events, offer_subdomain,
    procedure, serve_accompanying_document, serve_public_document,
    visits_offer,
)

admin.autodiscover()


urlpatterns = [
    path('', home, name='home'),
    path('accompanying', accompanying, name='accompanying'),
    path('accounts/', include('django_cas.urls', namespace='django_cas')),
    path('admin/holiday/import', core_views.import_holidays, name='import_holidays'),
    path('admin/', admin.site.urls),
    path('api/', include('immersionlyceens.libs.api.urls')),
    path('charts/', include('immersionlyceens.apps.charts.urls', namespace='charts')),
    path('core/', include('immersionlyceens.apps.core.urls')),
    path('dl/accdoc/<int:accompanying_document_id>', serve_accompanying_document, name='accompanying_document',),
    path('dl/pubdoc/<int:public_document_id>', serve_public_document, name='public_document',),
    path('geoapi/', include('immersionlyceens.libs.geoapi.urls')),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('immersion/', include('immersionlyceens.apps.immersion.urls', namespace='immersion')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('offer', offer, name='offer'),
    path('offer/<int:subdomain_id>', offer_subdomain, name='offer_subdomain'),
    path('offer_off_offer_events', offer_off_offer_events, name='offer_off_offer_events'),
    path('procedure', procedure, name='procedure'),
    path('shib_secure', include('shibboleth.urls', namespace='shibboleth')),
    path('shib/', shibbolethLogin, name='shibboleth_login'),
    path('summernote/', include('django_summernote.urls')),
    path('visits_offer', visits_offer, name='visits_offer')
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

handler500 = 'immersionlyceens.views.error_500'
