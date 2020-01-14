from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from hijack_admin.admin import HijackUserAdminMixin


from .models import (
    BachelorMention, Building, Campus, ImmersionUser,
    TrainingDomain, TrainingSubdomain
)

from .admin_forms import (
    BachelorMentionForm, BuildingForm, CampusForm,
    TrainingDomainForm, TrainingSubdomainForm,
)

class AdminWithRequest:
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


class TrainingDomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingDomainForm
    list_display = ('label', 'active')


class TrainingSubdomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingSubdomainForm
    list_display = ('label', 'training_domain', 'active')


class CampusAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CampusForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)


class BuildingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BuildingForm
    list_display = ('label', 'campus', 'url', 'active')
    list_filter = ('campus', 'active')
    search_fields = ('label',)


class BachelorMentionAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BachelorMentionForm
    list_display = ('label', 'active')


admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(BachelorMention, BachelorMentionAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Building, BuildingAdmin)
