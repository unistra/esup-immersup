from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack_admin.admin import HijackUserAdminMixin


from .models import (
    BachelorMention, Building, Campus, CourseDomain,
    ImmersionUser
)

from .admin_forms import (
    CourseDomainForm
)

class CourseDomainAdmin(admin.ModelAdmin):
    form = CourseDomainForm
    list_display = ('label', 'active')
    
    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super().get_form(request, obj, **kwargs)

        class AdminFormWithRequest(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return AdminFormWithRequest


class CustomUserAdmin(UserAdmin, HijackUserAdminMixin):
    #form = ImmersionUserChangeForm
    #add_form = ImmersionUserCreationForm

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2',
                       'email', 'first_name', 'last_name')
        }),
    )

    # add hijack button to display list of users
    list_display = ('username', 'email', 'first_name',
        'last_name', 'is_staff', 'hijack_field',)

    def __init__(self, model, admin_site):
        super(CustomUserAdmin, self).__init__(model, admin_site)
        self.form.admin_site = admin_site

    """
    class Media:
        js = (
            'js/immersion_user.js',  # app static folder
        )
        css = {
            'all': ('css/immersion.css',)
        }
    """


class CampusAdmin(admin.ModelAdmin):
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_update_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()


class BuildingAdmin(admin.ModelAdmin):
    list_display = ('label', 'campus', 'url', 'active')
    list_filter = ('campus', 'active')
    search_fields = ('label',)

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_update_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()


class BachelorMentionAdmin(admin.ModelAdmin):
    list_display = ('label', 'active')

    def has_module_permission(self, request):
        return True

    def has_view_permission(self, request, obj=None):
        return True

    def has_add_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()

    def has_update_permission(self, request, obj=None):
        return request.user.is_scuio_ip_manager()


admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(CourseDomain, CourseDomainAdmin)
admin.site.register(BachelorMention, BachelorMentionAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Building, BuildingAdmin)
