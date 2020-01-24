from datetime import datetime

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from hijack_admin.admin import HijackUserAdminMixin

from .admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm, CampusForm,
    CancelTypeForm, ComponentForm, CourseTypeForm, GeneralBachelorTeachingForm, HighSchoolForm,
    HolidayForm, ImmersionUserChangeForm, ImmersionUserCreationForm, PublicTypeForm,
    TrainingDomainForm, TrainingForm, TrainingSubdomainForm, UniversityYearForm, VacationForm,
)
from .models import (
    AccompanyingDocument, BachelorMention, Building, Calendar, Campus, CancelType, Component,
    Course, CourseType, GeneralBachelorTeaching, HighSchool, Holiday, ImmersionUser, PublicType,
    Training, TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)


class CustomAdminSite(admin.AdminSite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._registry.update(admin.site._registry)

    def find_in_list(self, l, value):
        try:
            return l.index(value)
        except ValueError:
            return 999

    def get_app_list(self, request):
        """
        Custom apps and models order
        """
        app_dict = self._build_app_dict(request)
        app_list = sorted(
            app_dict.values(),
            key=lambda x: self.find_in_list(settings.ADMIN_APPS_ORDER, x['app_label'].lower()),
        )

        for app in app_list:
            if not settings.ADMIN_MODELS_ORDER.get(app['app_label'].lower()):
                app['models'].sort(key=lambda x: x.get('app_label'))
            else:
                app['models'].sort(
                    key=lambda x: self.find_in_list(
                        settings.ADMIN_MODELS_ORDER[app['app_label'].lower()], x.get('object_name')
                    )
                )

            yield app

    def app_index(self, request, app_label, extra_context=None):
        """
        Custom order for app models
        """
        if settings.ADMIN_MODELS_ORDER.get(app_label):
            app_dict = self._build_app_dict(request, app_label)
            app_dict['models'].sort(
                key=lambda x: self.find_in_list(
                    settings.ADMIN_MODELS_ORDER[app_label], x.get('object_name')
                )
            )

            extra_context = {'app_list': [app_dict]}

        return super().app_index(request, app_label, extra_context)


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


class CustomUserAdmin(AdminWithRequest, UserAdmin, HijackUserAdminMixin):
    form = ImmersionUserChangeForm
    add_form = ImmersionUserCreationForm

    filter_horizontal = ('components', 'groups', 'user_permissions')

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'password1',
                    'password2',
                    'email',
                    'first_name',
                    'last_name',
                ),
            },
        ),
    )

    def __init__(self, model, admin_site):
        super(CustomUserAdmin, self).__init__(model, admin_site)
        self.form.admin_site = admin_site

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Disable delete
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        no_delete_msg = _("You don't have enough privileges to delete this account")

        if obj:
            if request.user.is_superuser:
                return True
            elif obj.is_superuser:
                messages.warning(request, no_delete_msg)
                return False

            # A user can only be deleted if not superuser and the authenticated user has
            # rights on ALL his groups
            if request.user.is_scuio_ip_manager():
                user_groups = obj.groups.all().values_list('name', flat=True)
                rights = settings.HAS_RIGHTS_ON_GROUP.get('SCUIO-IP')

                if not (set(x for x in user_groups) - set(rights)):
                    return True

            messages.warning(request, no_delete_msg)

            return False

    def has_change_permission(self, request, obj=None):
        if obj:
            if request.user.is_superuser or request.user == obj:
                return True
            elif obj.is_superuser:
                return False

            # A user can only be updated if not superuser and the authenticated user has
            # rights on ALL his groups
            if request.user.is_scuio_ip_manager():
                user_groups = obj.groups.all().values_list('name', flat=True)
                rights = settings.HAS_RIGHTS_ON_GROUP.get('SCUIO-IP')

                if not (set(x for x in user_groups) - set(rights)):
                    return True

            return False

        return True

    def get_list_display(self, request):
        list_display = ['username', 'email', 'first_name', 'last_name', 'is_superuser', 'is_staff']

        # add hijack button for admin users
        if request.user.is_superuser:
            list_display.append('hijack_field')

        return list_display

    def get_fieldsets(self, request, obj=None):
        # On user change, add Components in permissions fieldset
        # after Group selection
        if not obj:
            return super().get_fieldsets(request, obj)
        else:
            lst = list(UserAdmin.fieldsets)
            permissions_fields = list(lst[2])
            permissions_fields_list = list(permissions_fields[1]['fields'])
            permissions_fields_list.insert(4, 'components')

            if not request.user.is_superuser:
                # Remove components widget for non superusers
                try:
                    permissions_fields_list.remove('user_permissions')
                except ValueError:
                    pass

            lst[2] = ('Permissions', {'fields': tuple(permissions_fields_list)})

            fieldsets = tuple(lst)

        return fieldsets

    class Media:
        js = ('js/immersion_user.js',)  # implements user search
        css = {'all': ('css/immersionlyceens.css',)}


class TrainingDomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingDomainForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Disable delete
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and TrainingSubdomain.objects.filter(training_domain=obj).exists():
            messages.warning(
                request,
                _(
                    """This training domain can't be deleted """
                    """because it is used by training subdomains"""
                ),
            )
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
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Training.objects.filter(training_subdomains=obj).exists():
            messages.warning(
                request,
                _(
                    """This training subdomain can't be deleted """
                    """because it is used by a training"""
                ),
            )
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
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Building.objects.filter(campus=obj).exists():
            messages.warning(
                request,
                _("""This campus can't be deleted """ """because it is used by a building"""),
            )
            return False

        return True


class BuildingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BuildingForm
    list_display = ('label', 'campus', 'url', 'active')
    list_filter = ('campus', 'active')
    ordering = (
        'campus',
        'label',
    )
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
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Training.objects.filter(components=obj).exists():
            messages.warning(
                request,
                _("""This component can't be deleted """ """because it is used by a training"""),
            )
            return False

        return True


class TrainingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingForm
    filter_horizontal = (
        'components',
        'training_subdomains',
    )
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj and Course.objects.filter(training=obj).exists():
            messages.warning(
                request,
                _("""This training can't be deleted because """ """it is used by some courses"""),
            )
            return False

        return True


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
    list_display = (
        'label',
        'start_date',
        'end_date',
        'active',
    )
    list_filter = ('active',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = ['active', 'purge_date']
        if obj:
            if obj.purge_date is not None:
                return list(
                    set(
                        [field.name for field in self.opts.local_fields]
                        + [field.name for field in self.opts.local_many_to_many]
                    )
                )

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
                messages.warning(
                    request,
                    _(
                        """This component can't be deleted """
                        """because university year has already started"""
                    ),
                )
                return False
            elif obj.purge_date is not None:
                messages.warning(
                    request,
                    _(
                        """This component can't be deleted """
                        """because a purge date is defined"""
                    ),
                )
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
    list_display = (
        'label',
        'start_date',
        'end_date',
        'active',
    )
    list_filter = ('active',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = ['active', 'purge_date']
        if obj:
            if obj.purge_date is not None:
                return list(
                    set(
                        [field.name for field in self.opts.local_fields]
                        + [field.name for field in self.opts.local_many_to_many]
                    )
                )

            elif obj.start_date <= datetime.today().date():
                fields.append('start_date')
        return fields

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_scuio_ip_manager():
            return False

        if obj:
            if obj.start_date <= datetime.today().date():
                messages.warning(
                    request,
                    _(
                        """This component can't be deleted """
                        """because university year has already started"""
                    ),
                )
                return False
            elif obj.purge_date is not None:
                messages.warning(
                    request,
                    _(
                        """This component can't be deleted """
                        """because a purge date is defined"""
                    ),
                )
                return False

        return True


class CalendarAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CalendarForm
    list_display = ('label',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = []
        if obj:

            # global evaluation date
            if (obj.year_start_date and obj.year_start_date <= datetime.today().date()) or (
                obj.global_evaluation_date
                and obj.global_evaluation_date <= datetime.today().date()
            ):
                fields.append('global_evaluation_date')

            # year_start > today
            if obj.year_start_date and obj.year_start_date <= datetime.today().date():
                fields.append('year_start_date')

            # semester1_start > today
            if obj.semester1_start_date and obj.semester1_start_date <= datetime.today().date():
                fields.append('year_start_date')
                fields.append('calendar_mode')
            # semester1_end > today
            if obj.semester1_end_date and obj.semester1_end_date <= datetime.today().date():
                fields.append('semester1_end_date')
                fields.append('semester1_registration_start_date')

            # semester2_start > today
            if obj.semester2_start_date and obj.semester2_start_date <= datetime.today().date():
                fields.append('year_start_date')
            # semester2_end > today
            if obj.semester2_end_date and obj.semester2_end_date <= datetime.today().date():
                fields.append('semester1_end_date')
                fields.append('semester1_registration_start_date')

        return fields

    def has_add_permission(self, request):
        """Singleton"""
        return not Calendar.objects.exists()

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_calendar.js',
        )


class HighSchoolAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HighSchoolForm
    list_display = (
        'label',
        'city',
        'email',
        'head_teacher_name',
        'referent_name',
        'convention_start_date',
        'convention_end_date',
    )
    list_filter = ('city',)
    ordering = ('label',)
    search_fields = ('label', 'city', 'head_teacher_name', 'referent_name')

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def has_delete_permission(self, request, obj=None):
        # Only superadmin could delete Highschool items
        # TODO: maybe only use model groups rights !!!
        if request.user.is_superuser:
            return True

        return False

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        if settings.USE_GEOAPI:
            js = (
                'js/jquery-3.4.1.slim.min.js',
                'js/admin_highschool.js',
            )


class AccompanyingDocumentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = AccompanyingDocumentForm
    # list_display = ('label', 'description', 'public_type', 'fileUrl')
    ordering = ('label',)
    search_fields = ('label', 'fileName')
    list_filter = ('public_type',)

    # def fileUrl(self, obj):
    #     if obj.document:
    #         return format_html(f'<a href="{obj.document.url}">{obj.document.url}</a>')
    #     else:
    #         return format_html('<a href=""></a>')

    def get_list_display(self, request):

        def file_url(obj):
            url = request.build_absolute_uri(reverse('accompanying_document', args=(obj.pk, )))
            return format_html(f'<a href="{url}">{url}</a>')
            
        file_url.short_description = _('Address')

        return (
            'label', 'description', 'public_type', file_url,
        )

    # file_url.short_description = _("Document Address")



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
admin.site.register(AccompanyingDocument, AccompanyingDocumentAdmin)
