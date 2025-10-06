from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from immersionlyceens.apps.immersion.views import shibbolethLogin

from .apps.core import views as core_views
from .views import (
    accompanying, charter_not_signed, faq, highschools, home,
    host_establishments, offer, offer_off_offer_events, offer_subdomain,
    procedure, search_slots, serve_accompanying_document, serve_attestation_document,
    serve_immersion_group_document, serve_public_document, cohort_offer, cohort_offer_subdomain
)

admin.autodiscover()

urlpatterns = [
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('', home, name='home'),
    path('accompanying', accompanying, name='accompanying'),
    path("accounts/", include("django.contrib.auth.urls")),
    path('highschools', highschools, name='highschools'),
    path('cas_accounts/', include('django_cas.urls', namespace='django_cas')),
    path('charter_not_signed', charter_not_signed, name='charter_not_signed'),
    path('admin/holiday/import', core_views.import_holidays, name='import_holidays'),
    path('admin/', admin.site.urls),
    path('api/', include('immersionlyceens.apps.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('charts/', include('immersionlyceens.apps.charts.urls', namespace='charts')),
    path('core/', include('immersionlyceens.apps.core.urls')),
    path(
        'dl/accdoc/<int:accompanying_document_id>',
        serve_accompanying_document,
        name='accompanying_document',
    ),
    path(
        'dl/pubdoc/<int:public_document_id>',
        serve_public_document,
        name='public_document',
    ),
    path(
        'dl/attestation/<int:attestation_document_id>',
        serve_attestation_document,
        name='attestation_document',
    ),
    path(
        'dl/immersiongroup/<int:immersion_group_id>',
        serve_immersion_group_document,
        name='group_document',
    ),
    path('faq', faq, name='faq'),
    path('geoapi/', include('immersionlyceens.libs.geoapi.urls')),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('host_establishments/', host_establishments, name='host_establishments'),
    path('immersion/', include('immersionlyceens.apps.immersion.urls', namespace='immersion')),
    path('offer', offer, name='offer'),
    path('offer/<int:subdomain_id>', offer_subdomain, name='offer_subdomain'),
    path('cohort_offer/<int:subdomain_id>', cohort_offer_subdomain, name='cohort_offer_subdomain'),
    path('offer_off_offer_events', offer_off_offer_events, name='offer_off_offer_events'),
    path('procedure', procedure, name='procedure'),
    path('search_slots', search_slots, name='search_slots'),
    path('shib_secure/', include('shibboleth.urls', namespace='shibboleth')),
    path('shib/', shibbolethLogin, name='shibboleth_login'),
    # path('ckeditor/', include('ckeditor_uploader.urls')),
    path('cohort_offer', cohort_offer, name='cohort_offer'),
    path("ckeditor5/", include('django_ckeditor_5.urls')),
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
