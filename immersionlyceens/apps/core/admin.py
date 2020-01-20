from datetime import datetime

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from hijack_admin.admin import HijackUserAdminMixin

from .admin_forms import (BachelorMentionForm, BuildingForm, CalendarForm,
                          CampusForm, CancelTypeForm, ComponentForm,
                          CourseTypeForm, GeneralBachelorTeachingForm,
                          HighSchoolForm, HolidayForm,
                          ImmersionUserCreationForm, PublicTypeForm,
                          TrainingDomainForm, TrainingForm,
                          TrainingSubdomainForm, UniversityYearForm,
                          VacationForm)
from .models import (BachelorMention, Building, Calendar, Campus, CancelType,
                     Component, CourseType, GeneralBachelorTeaching,
                     HighSchool, Holiday, ImmersionUser, PublicType, Training,
                     TrainingDomain, TrainingSubdomain, UniversityYear,
                     Vacation)


class CustomAdminSite(admin.AdminSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry.update(admin.site._registry)

    def get_app_list(self, request):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        ordering = {
            'ImmersionUser': 1,
            'UniversityYear': 2,
            'HighSchool': 3,
            'GeneralBachelorTeaching': 4,
            'BachelorMention': 5,
            'Campus': 6,
            'Building': 7,
            'Component': 8,
            'TrainingDomain': 9,
            'TrainingSubdomain': 10,
            'Training': 11,
            'CourseType': 12,
            'PublicType': 13,
            'CancelType': 14,
            'Holiday': 15,
            'Vacation': 16,
            'Calendar': 17,
        }

        app_dict = self._build_app_dict(request)

        # Sort the apps alphabetically.
        app_list = sorted(app_dict.values(), key=lambda x: x['name'].lower())

        # Sort the models alphabetically within each app.
        # key=lambda x: x['name']
        for app in app_list:
            app['models'].sort(key=lambda x: ordering.get(x.get('object_name')))

        return app_list


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
            'js/immersion_user.js',  # implements user search
        )
        css = {
            'all': ('css/immersionlyceens.css',)
        }


class TrainingDomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingDomainForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label', )
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
    ordering = ('label',)
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
            messages.warning(request, _(
                """This training subdomain can't be deleted """
                """because it is used by a training"""))
            return False

        return True


class CampusAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CampusForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        del actions['delete_selected']
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Building.objects.filter(campus=obj).exists():
            messages.warning(request, _(
                """This campus can't be deleted """
                """because it is used by a building"""))
            return False

        return True


class BuildingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BuildingForm
    list_display = ('label', 'campus', 'url', 'active')
    list_filter = ('campus', 'active')
    ordering = ('campus', 'label',)
    search_fields = ('label',)


class BachelorMentionAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BachelorMentionForm
    list_display = ('label', 'active')
    ordering = ('label',)


class GeneralBachelorTeachingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = GeneralBachelorTeachingForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)


class ComponentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = ComponentForm
    list_display = ('code', 'label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
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
            messages.warning(request, _(
                """This component can't be deleted """
                """because it is used by a training"""))
            return False

        return True


class TrainingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingForm
    filter_horizontal = ('components', 'training_subdomains', )
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)


class CancelTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CancelTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)


class CourseTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CourseTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)


class PublicTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = PublicTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)


class UniversityYearAdmin(AdminWithRequest, admin.ModelAdmin):
    form = UniversityYearForm
    list_display = ('label', 'start_date', 'end_date', 'active',)
    list_filter = ('active',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = ['active', 'purge_date']
        if obj:
            if obj.purge_date is not None:
                return list(set(
                    [field.name for field in self.opts.local_fields] +
                    [field.name for field in self.opts.local_many_to_many]
                ))

            elif obj.start_date <= datetime.today().date():
                fields.append('start_date')
        return fields

    # def get_actions(self, request):
    #     # Disable delete
    #     actions = super().get_actions(request)
    #     del actions['delete_selected']
    #     return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj:
            if obj.start_date <= datetime.today().date():
                messages.warning(request, _(
                    """This component can't be deleted """
                    """because university year has already started"""))
                return False
            elif obj.purge_date is not None:
                messages.warning(request, _(
                    """This component can't be deleted """
                    """because a purge date is defined"""))
                return False

        return True


class HolidayAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HolidayForm
    list_display = ('label', 'date')


class VacationAdmin(AdminWithRequest, admin.ModelAdmin):
    form = VacationForm
    list_display = ('label', 'start_date', 'end_date')


class UniversityYearAdmin(AdminWithRequest, admin.ModelAdmin):
    form = UniversityYearForm
    list_display = ('label', 'start_date', 'end_date', 'active',)
    list_filter = ('active',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = ['active', 'purge_date']
        if obj:
            if obj.purge_date is not None:
                return list(set(
                    [field.name for field in self.opts.local_fields] +
                    [field.name for field in self.opts.local_many_to_many]
                ))

            elif obj.start_date <= datetime.today().date():
                fields.append('start_date')
        return fields

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj:
            print(obj.start_date)
            if obj.start_date <= datetime.today().date():
                messages.warning(request, _("""This component can't be deleted """
                    """because university year has already started"""))
                return False
            elif obj.purge_date is not None:
                messages.warning(request, _("""This component can't be deleted """
                    """because a purge date is defined"""))
                return False

        return True


class CalendarAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CalendarForm
    list_display = ('label',)
    search_fields = ('label',)

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_calendar.js',
        )


class HighSchoolAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HighSchoolForm
    list_display = ('label', 'city', 'email', 'head_teacher_name',
        'referent_name', 'convention_start_date', 'convention_end_date')
    list_filter = ('city',)
    ordering = ('label',)
    search_fields = ('label', 'label', 'head_teacher_name', 'referent_name')

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_highschool.js',
        )

admin.site = CustomAdminSite(name='Repositories')

admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Component, ComponentAdmin)
admin.site.register(BachelorMention, BachelorMentionAdmin)
admin.site.register(Campus, CampusAdmin)
admin.site.register(Building, BuildingAdmin)
admin.site.register(HighSchool, HighSchoolAdmin)
admin.site.register(CancelType, CancelTypeAdmin)
admin.site.register(CourseType, CourseTypeAdmin)
admin.site.register(GeneralBachelorTeaching, GeneralBachelorTeachingAdmin)
admin.site.register(PublicType, PublicTypeAdmin)
admin.site.register(UniversityYear, UniversityYearAdmin)
admin.site.register(Holiday, HolidayAdmin)
admin.site.register(Vacation, VacationAdmin)
admin.site.register(Calendar, CalendarAdmin)
# Hide Site django app
# commented out : break reverse url for /admin/auth/group/
# admin.site.unregister(Site)
