from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack_admin.admin import HijackUserAdminMixin

from .admin_forms import (BuildingForm, CampusForm, CourseDomainForm,
                          HighSchoolForm)
from .models import (BachelorMention, Building, Campus, CourseDomain,
                     HighSchool, ImmersionUser)


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
    form = CampusForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)

    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super().get_form(request, obj, **kwargs)

        class AdminFormWithRequest(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return AdminFormWithRequest


class BuildingAdmin(admin.ModelAdmin):
    form = BuildingForm
    list_display = ('label', 'campus', 'url', 'active')
    list_filter = ('campus', 'active')
    search_fields = ('label',)

    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super().get_form(request, obj, **kwargs)

        class AdminFormWithRequest(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return AdminFormWithRequest


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


class HighSchoolAdmin(admin.ModelAdmin):
    form = HighSchoolForm
    list_display = ('label', 'city', 'email', 'head_teacher_name',
                    'referent_name', 'convention_start_date', 'convention_end_date')
    list_filter = ('city',)
    search_fields = ('label', 'label', 'head_teacher_name', 'referent_name')

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_highschool.js',
        )

    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super().get_form(request, obj, **kwargs)

        class AdminFormWithRequest(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return AdminFormWithRequest


admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(CourseDomain, CourseDomainAdmin)
admin.site.register(BachelorMention, BachelorMentionAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(HighSchool, HighSchoolAdmin)
