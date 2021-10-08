from datetime import datetime

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext_lazy as _
from django_summernote.admin import SummernoteModelAdmin
from django_json_widget.widgets import JSONEditorWidget
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

from .admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm, CampusForm, CancelTypeForm,
    CertificateLogoForm, CertificateSignatureForm, StructureForm, CourseTypeForm, EstablishmentForm,
    EvaluationFormLinkForm, EvaluationTypeForm, GeneralBachelorTeachingForm, GeneralSettingsForm, HighSchoolForm,
    HolidayForm, ImmersionUserChangeForm, ImmersionUserCreationForm, InformationTextForm, MailTemplateForm,
    PublicDocumentForm, PublicTypeForm, TrainingDomainForm, TrainingForm, TrainingSubdomainForm, UniversityYearForm,
    VacationForm,
)
from .models import (
    AccompanyingDocument, AnnualStatistics, BachelorMention, Building, Calendar, Campus, CancelType, CertificateLogo,
    CertificateSignature, Structure, Course, CourseType, Establishment, EvaluationFormLink, EvaluationType,
    GeneralBachelorTeaching, GeneralSettings, HighSchool, Holiday, Immersion, ImmersionUser, InformationText,
    MailTemplate, PublicDocument, PublicType, Slot, Training, TrainingDomain, TrainingSubdomain, UniversityYear,
    Vacation,
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
            app_dict.values(), key=lambda x: self.find_in_list(settings.ADMIN_APPS_ORDER, x['app_label'].lower()),
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
                key=lambda x: self.find_in_list(settings.ADMIN_MODELS_ORDER[app_label], x.get('object_name'))
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


class ActivationFilter(admin.SimpleListFilter):
    title = _('Activated accounts')
    parameter_name = 'validation_string'

    def lookups(self, request, model_admin):
        return [('True', _('Yes')), ('False', _('No'))]

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(groups__name__in=['LYC', 'ETU'], validation_string__isnull=True)
        elif self.value() == 'False':
            return queryset.filter(groups__name__in=['LYC', 'ETU'], validation_string__isnull=False)


class CustomUserAdmin(AdminWithRequest, UserAdmin):
    form = ImmersionUserChangeForm
    add_form = ImmersionUserCreationForm

    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_superuser',
        'is_staff',
        'get_groups_list',
        'get_activated_account',
        'destruction_date',
    ]

    list_filter = ('is_staff', 'is_superuser', ActivationFilter, 'groups')

    def get_activated_account(self, obj):
        if not obj.is_superuser and (obj.is_high_school_student() or obj.is_student()):
            if obj.is_valid():
                return _('Yes')
            else:
                return _('No')
        else:
            return ''

    def get_groups_list(self, obj):
        return [group.name for group in obj.groups.all().order_by('name')]

    get_activated_account.short_description = _('Activated account')
    get_groups_list.short_description = _('Groups')

    filter_horizontal = ('structures', 'groups', 'user_permissions')

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('establishment', 'username', 'password1', 'password2', 'email', 'first_name', 'last_name',),
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
            if request.user.is_ref_etab_manager():
                user_groups = obj.groups.all().values_list('name', flat=True)
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB')

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
            if request.user.is_ref_etab_manager():
                user_groups = obj.groups.all().values_list('name', flat=True)
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB')

                if not (set(x for x in user_groups) - set(rights)):
                    return True

            return False

        return True

    def get_fieldsets(self, request, obj=None):
        # On user change, add structures in permissions fieldset
        # after Group selection
        if not obj:
            return super().get_fieldsets(request, obj)
        else:
            lst = list(UserAdmin.fieldsets)
            permissions_fields = list(lst[2])
            permissions_fields_list = list(permissions_fields[1]['fields'])
            permissions_fields_list.insert(4, 'structures')
            permissions_fields_list.insert(5, 'highschool')

            if not request.user.is_superuser:
                # Remove structures widget for non superusers
                try:
                    permissions_fields_list.remove('user_permissions')
                except ValueError:
                    pass

            lst[2] = ('Permissions', {'fields': tuple(permissions_fields_list)})

            fieldsets = tuple(lst)

        return fieldsets

    class Media:
        js = ('js/immersion_user.min.js',)  # implements user search
        css = {'all': ('css/immersionlyceens.min.css',)}


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
        if not request.user.is_ref_etab_manager():
            return False

        if obj and TrainingSubdomain.objects.filter(training_domain=obj).exists():
            messages.warning(
                request,
                _("""This training domain can't be deleted """ """because it is used by training subdomains"""),
            )
            return False

        return True


class TrainingSubdomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingSubdomainForm
    list_display = ('label', 'training_domain', 'active')
    list_filter = (
        'training_domain',
        'active',
    )
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
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Training.objects.filter(training_subdomains=obj).exists():
            messages.warning(
                request, _("""This training subdomain can't be deleted """ """because it is used by a training"""),
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
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Building.objects.filter(campus=obj).exists():
            messages.warning(request, _("This campus can't be deleted because it is used by a building"))
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
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Slot.objects.filter(building=obj).exists():
            messages.warning(request, _("This building can't be deleted because it is used by a slot"))
            return False

        return True


class BachelorMentionAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BachelorMentionForm
    list_display = ('label', 'active')
    ordering = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and HighSchoolStudentRecord.objects.filter(technological_bachelor_mention=obj).exists():
            messages.warning(
                request,
                _(
                    """This bachelor mention can't be deleted """
                    """because it is used by a high-school student record"""
                ),
            )
            return False

        return True


class GeneralBachelorTeachingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = GeneralBachelorTeachingForm
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and HighSchoolStudentRecord.objects.filter(general_bachelor_teachings=obj).exists():
            messages.warning(
                request,
                _("""This teaching can't be deleted """ """because it is used by a high-school student record"""),
            )
            return False

        return True


class EstablishementAdmin(AdminWithRequest, admin.ModelAdmin):
    form = EstablishmentForm
    list_display = ('code', 'label', 'master', 'active', )
    list_filter = ('active',)
    ordering = ('master', 'label', )
    search_fields = ('label',)

    formfield_overrides = {
        models.JSONField: {'widget': JSONEditorWidget},
    }

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
        if not request.user.is_superuser:
            return False

        # Test existing data before deletion (see US 160)
        """
        if obj and Training.objects.filter(components=obj).exists():
            messages.warning(request, _("This establishment can't be deleted"))
            return False
        """

        return True


class StructureAdmin(AdminWithRequest, admin.ModelAdmin):
    form = StructureForm
    list_display = ('code', 'label', 'active', 'mailing_list')
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
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Training.objects.filter(structures=obj).exists():
            messages.warning(request, _("This structure can't be deleted because it is used by a training"))
            return False

        return True


class TrainingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingForm
    filter_horizontal = ('structures', 'training_subdomains')
    list_display = ('label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Course.objects.filter(training=obj).exists():
            messages.warning(
                request, _("This training can't be deleted because it is used by some courses"),
            )
            return False

        return True


class CancelTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CancelTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Immersion.objects.filter(cancellation_type=obj).exists():
            messages.warning(
                request, _("This cancellation type can't be deleted because it is used by some registrations"),
            )
            return False

        return True


class CourseTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CourseTypeForm
    list_display = ('label', 'full_label', 'active')
    ordering = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and Slot.objects.filter(course_type=obj).exists():
            messages.warning(
                request, _("This course type can't be deleted because it is used by some slots"),
            )
            return False

        return True


class PublicTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = PublicTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj and AccompanyingDocument.objects.filter(public_type=obj).exists():
            messages.warning(
                request,
                _("""This public type can't be deleted """ """because it is used by accompanying document(s)"""),
            )
            return False

        return True


class UniversityYearAdmin(AdminWithRequest, admin.ModelAdmin):
    form = UniversityYearForm
    list_display = ('label', 'start_date', 'end_date', 'active')
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

        return fields

    # def get_actions(self, request):
    #     # Disable delete
    #     actions = super().get_actions(request)
    #     del actions['delete_selected']
    #     return actions

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj:
            if obj.start_date <= datetime.today().date():
                messages.warning(
                    request,
                    _("""This university year can't be deleted """ """because university year has already started"""),
                )
                return False
            elif obj.purge_date is not None:
                messages.warning(
                    request, _("""This university year can't be deleted """ """because a purge date is defined"""),
                )
                return False

        return True


class HolidayAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HolidayForm
    list_display = ('label', 'date')

    def has_delete_permission(self, request, obj=None):
        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True


class VacationAdmin(AdminWithRequest, admin.ModelAdmin):
    form = VacationForm
    list_display = ('label', 'start_date', 'end_date')

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)
        if len(univ_years) <= 0:
            return True
        univ_year = univ_years[0]

        if now >= univ_year.start_date:
            return False

        return True


class UniversityYearAdmin(AdminWithRequest, admin.ModelAdmin):
    form = UniversityYearForm
    list_display = (
        'label',
        'start_date',
        'end_date',
        'purge_date',
        'active',
    )
    list_filter = ('active',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        fields = ['active', 'purge_date']
        if request.user.is_superuser:
            return fields
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

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        elif request.user.is_ref_etab_manager():
            return not (UniversityYear.objects.filter(purge_date__isnull=True).count() > 0)
        else:
            return False

    def has_delete_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True
        if not request.user.is_ref_etab_manager():
            return False

        if obj:
            if obj.start_date <= datetime.today().date() <= obj.end_date:
                messages.warning(
                    request,
                    _("""This university year can't be deleted """ """because university year has already started"""),
                )
                return False
            elif obj.purge_date is not None:
                messages.warning(request, _("This university year can't be deleted because a purge date is defined"))
                return False

        return True


class CalendarAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CalendarForm
    list_display = ('label',)
    search_fields = ('label',)
    fieldsets = (
        (None, {'fields': ('label', 'calendar_mode', 'global_evaluation_date')}),
        (
            _('Year mode'),
            {
                'fields': (
                    'year_nb_authorized_immersion',
                    'year_registration_start_date',
                    'year_start_date',
                    'year_end_date',
                )
            },
        ),
        (
            _('Semester mode'),
            {
                'fields': (
                    'nb_authorized_immersion_per_semester',
                    'semester1_registration_start_date',
                    'semester2_registration_start_date',
                )
            },
        ),
        (_('Semester 1'), {'fields': ('semester1_start_date', 'semester1_end_date',)}),
        (_('Semester 2'), {'fields': ('semester2_start_date', 'semester2_end_date',)}),
    )

    def get_readonly_fields(self, request, obj=None):
        fields = []

        uy = None
        university_years = UniversityYear.objects.filter(active=True)
        if university_years.count() > 0:
            uy = university_years[0]

        if uy is None or request.user.is_superuser:
            return []

        if obj:
            if uy.start_date <= datetime.today().date():
                fields = [
                    'label',
                    'calendar_mode',
                    'year_start_date',
                    'year_end_date',
                    'semester1_start_date',
                    'semester1_end_date',
                    'semester2_start_date',
                    'semester2_end_date',
                    'year_registration_start_date',
                    'semester1_registration_start_date',
                    'semester2_registration_start_date',
                    'year_nb_authorized_immersion',
                    'nb_authorized_immersion_per_semester',
                ]

            if uy.end_date <= datetime.today().date():
                fields.append('global_evaluation_date')

        return list(set(fields))

    def has_add_permission(self, request):
        """Singleton"""
        return not Calendar.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_calendar.min.js',
        )


class HighSchoolAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HighSchoolForm
    list_display = (
        'label',
        'city',
        'email',
        'head_teacher_name',
        'referents_list',
        'convention_start_date',
        'convention_end_date',
    )
    list_filter = ('city',)
    ordering = ('label',)
    search_fields = ('label', 'city', 'head_teacher_name')

    def referents_list(self, obj):
        return [
            "%s %s" % (user.last_name, user.first_name)
            for user in obj.highschool_referent.all().order_by('last_name', 'first_name')
        ]

    referents_list.short_description = _('Referents')

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
        return request.user.is_superuser

    class Media:
        # TODO: check why I can't use django.jquery stuff !!!!!
        if settings.USE_GEOAPI:
            js = (
                'js/jquery-3.4.1.slim.min.js',
                'js/admin_highschool.min.js',
            )


class InformationTextAdmin(AdminWithRequest, admin.ModelAdmin):
    form = InformationTextForm
    list_display = ('label', 'code', 'active')
    list_filter = ('label', 'code')
    ordering = ('label',)
    search_fields = ('label', 'code', 'active')

    def get_readonly_fields(self, request, obj=None):
        fields = []
        if obj:
            if not request.user.is_superuser:
                fields.append('description')
            if obj.label:
                fields.append('label')
            if obj.code:
                fields.append('code')
        return fields

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    class Media:
        css = {
            'all': (
                'css/immersionlyceens.min.css',
                'js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.css',
                'js/vendor/datatables/datatables.min.css',
                'js/vendor/datatables/DataTables-1.10.20/css/dataTables.jqueryui.min.css',
            )
        }
        js = (
            'js/vendor/jquery/jquery-3.4.1.min.js',
            'js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.js',
            'js/admin_information_text.min.js',
            'js/vendor/datatables/datatables.min.js',
            'js/vendor/datatables/DataTables-1.10.20/js/dataTables.jqueryui.min.js',
        )


class AccompanyingDocumentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = AccompanyingDocumentForm
    ordering = ('label',)
    search_fields = ('label',)
    list_filter = ('public_type', 'active')

    def get_list_display(self, request):
        def file_url(obj):
            url = request.build_absolute_uri(reverse('accompanying_document', args=(obj.pk,)))
            return format_html(f'<a href="{url}">{url}</a>')

        file_url.short_description = _('Address')
        return ('label', 'description', 'get_types', file_url, 'active')


class PublicDocumentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = PublicDocumentForm
    ordering = ('label',)
    search_fields = ('label',)
    list_filter = ('published',)
    readonly_fields = ('published',)

    def get_list_display(self, request):
        def file_url(obj):
            url = request.build_absolute_uri(reverse('public_document', args=(obj.pk,)))
            return format_html(f'<a href="{url}">{url}</a>')

        def doc_used_in(obj):

            used_docs = []

            texts_docs_id = obj.get_all_texts_id()
            docs = InformationText.objects.filter(id__in=texts_docs_id)

            return format_html_join(
                '',
                '<a href="{}">{}</a><br>',
                (
                    (
                        reverse('admin:{}_{}_change'.format(doc._meta.app_label, doc._meta.model_name), args=(doc.pk,)),
                        doc.label,
                    )
                    for doc in docs
                ),
            )

        file_url.short_description = _('Address')
        doc_used_in.short_description = _('Used in')

        return ('label', file_url, doc_used_in, 'active', 'published')

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_ref_etab_manager():
            return False

        if obj:
            if obj.published:
                messages.warning(
                    request, _("This document is used in public interface : deletion not allowed "),
                )
                return False

        return True


class MailTemplateAdmin(AdminWithRequest, SummernoteModelAdmin):
    form = MailTemplateForm
    list_display = ('code', 'label')
    filter_horizontal = ('available_vars',)
    summernote_fields = ('body',)

    def has_delete_permission(self, request, obj=None):
        # Only a superuser can delete a template
        return request.user.is_superuser

    class Media:
        css = {
            'all': (
                'css/immersionlyceens.min.css',
                'js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.css',
                'js/vendor/datatables/datatables.min.css',
                'js/vendor/datatables/DataTables-1.10.20/css/dataTables.jqueryui.min.css',
            )
        }
        js = (
            'js/vendor/jquery/jquery-3.4.1.min.js',
            'js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.js',
            'js/immersion_mail_templates.min.js',
            'js/vendor/datatables/datatables.min.js',
            'js/vendor/datatables/DataTables-1.10.20/js/dataTables.jqueryui.min.js',
        )


class EvaluationTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = EvaluationTypeForm
    list_display = ('code', 'label')
    ordering = ('label',)


class EvaluationFormLinkAdmin(AdminWithRequest, admin.ModelAdmin):
    form = EvaluationFormLinkForm
    list_display = (
        "evaluation_type",
        "url",
    )
    ordering = ('evaluation_type',)

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [
                'evaluation_type',
            ]
        return self.readonly_fields


class GeneralSettingsAdmin(AdminWithRequest, admin.ModelAdmin):
    form = GeneralSettingsForm
    list_display = ('setting', 'value', 'description')
    ordering = ('setting',)


class AnnualStatisticsAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = (
        'year',
        'platform_registrations',
        'one_immersion_registrations',
        'multiple_immersions_registrations',
        'participants_one_immersion',
        'participants_multiple_immersions',
        'immersion_registrations',
        'structures_count',
        'trainings_one_slot_count',
        'courses_one_slot_count',
        'total_slots_count',
        'seats_count',
        'approved_highschools',
        'highschools_without_students',
    )
    ordering = ('-year',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    class Media:
        css = {
            'all': (
                'css/immersionlyceens.min.css',
                'css/admin_annual_stats.min.css',
            )
        }


class CertificateLogoAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CertificateLogoForm

    def show_logo(self, obj):
        return format_html(f'<img src="{obj.logo.url}">')

    list_display = [
        'show_logo',
    ]

    show_logo.short_description = _('Certificate logo')


class CertificateSignatureAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CertificateSignatureForm

    def show_signature(self, obj):
        return format_html(f'<img src="{obj.signature.url}">')

    list_display = [
        'show_signature',
    ]

    show_signature.short_description = _('Certificate signature')


admin.site = CustomAdminSite(name='Repositories')

admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Establishment, EstablishementAdmin)
admin.site.register(Structure, StructureAdmin)
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
admin.site.register(MailTemplate, MailTemplateAdmin)
admin.site.register(InformationText, InformationTextAdmin)
admin.site.register(AccompanyingDocument, AccompanyingDocumentAdmin)
admin.site.register(PublicDocument, PublicDocumentAdmin)
admin.site.register(EvaluationFormLink, EvaluationFormLinkAdmin)
admin.site.register(EvaluationType, EvaluationTypeAdmin)
admin.site.register(GeneralSettings, GeneralSettingsAdmin)
admin.site.register(AnnualStatistics, AnnualStatisticsAdmin)
admin.site.register(CertificateLogo, CertificateLogoAdmin)
admin.site.register(CertificateSignature, CertificateSignatureAdmin)
