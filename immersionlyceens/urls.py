from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from .apps.core import views as core_views
from .views import home, serve_accompanying_document

admin.autodiscover()

urlpatterns = [
    # Examples:
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    # path('core/', include('immersionlyceens.apps.core.urls')),
    path('accounts/', include('django_cas.urls', namespace='django_cas')),
    path('hijack/', include('hijack.urls', namespace='hijack')),
    path('api/', include('immersionlyceens.libs.api.urls')),
    path('geoapi/', include('immersionlyceens.libs.geoapi.urls')),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path(
        'dl/<int:accompanying_document_id>',
        serve_accompanying_document,
        name='accompanying_document',
    ),
    path('admin/holiday/import', core_views.import_holidays, name='import_holidays'),
    path('summernote/', include('django_summernote.urls')),
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
