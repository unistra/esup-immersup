from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from hijack_admin.admin import HijackUserAdminMixin

from .models import (
    BachelorMention, Building, Campus, CancelType, Component,
    CourseType, GeneralBachelorTeaching, ImmersionUser,
    PublicType, Training, TrainingDomain, TrainingSubdomain,
)

from .admin_forms import (
    BachelorMentionForm, BuildingForm, CampusForm,
    CancelTypeForm, ComponentForm, CourseTypeForm,
    GeneralBachelorTeachingForm, ImmersionUserCreationForm,
    PublicTypeForm, TrainingForm, TrainingDomainForm,
    TrainingSubdomainForm,
)

class AdminWithRequest:
    """
    Class used to pass request object to admin form
    """
    def get_form(self, request, obj=None, **kwargs):
        AdminForm = super().get_form(request, obj, **kwargs)

        class AdminFormWithRequest(AdminForm):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return AdminForm(*args, **kwargs)

        return AdminFormWithRequest


class CustomUserAdmin(UserAdmin, HijackUserAdminMixin):
    #form = ImmersionUserChangeForm
    add_form = ImmersionUserCreationForm

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


    class Media:
        js = (
            # 'js/jquery-3.4.1.slim.min.js',
            'js/immersion_user.js',  # app static folder
        )
        css = {
            'all': ('css/immersionlyceens.css',)
        }


class TrainingDomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingDomainForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and TrainingSubdomain.objects.filter(
                training_domain=obj).exists():
            messages.warning(request, _("""This training domain can't be deleted """
                """because it is used by training subdomains"""))
            return False

        return True


class TrainingSubdomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingSubdomainForm
    list_display = ('label', 'training_domain', 'active')
    list_filter = ('active',)
    search_fields = ('label',)

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Training.objects.filter(training_subdomains=obj).exists():
            messages.warning(request, _("""This training subdomain can't be deleted """
                """because it is used by a training"""))
            return False

        return True


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


class GeneralBachelorTeachingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = GeneralBachelorTeachingForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)


class ComponentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = ComponentForm
    list_display = ('code', 'label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Training.objects.filter(components=obj).exists():
            messages.warning(request, _("""This component can't be deleted """
                """because it is used by a training"""))
            return False

        return True


class TrainingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingForm
    filter_horizontal = ('components', 'training_subdomains', )
    list_display = ('label', 'active')
    list_filter = ('active',)
    search_fields = ('label',)


class CancelTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CancelTypeForm
    list_display = ('label', 'active')


class CourseTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CourseTypeForm
    list_display = ('label', 'active')


class PublicTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = PublicTypeForm
    list_display = ('label', 'active')


admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Component, ComponentAdmin)
admin.site.register(BachelorMention, BachelorMentionAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(CancelType, CancelTypeAdmin)
admin.site.register(CourseType, CourseTypeAdmin)
admin.site.register(GeneralBachelorTeaching, GeneralBachelorTeachingAdmin)
admin.site.register(PublicType, PublicTypeAdmin)
