from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack_admin.admin import HijackUserAdminMixin

from .models import (
    CourseDomain, ImmersionUser
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

admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(CourseDomain, CourseDomainAdmin)
