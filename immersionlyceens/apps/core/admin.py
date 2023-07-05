import logging

from datetime import datetime

from adminsortable2.admin import SortableAdminMixin
from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import JSONField, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext, gettext_lazy as _
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, RelatedDropdownFilter,
)
from django_json_widget.widgets import JSONEditorWidget
from django_summernote.admin import SummernoteModelAdmin
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy

from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, HighSchoolStudentRecordDocument, StudentRecord,
    VisitorRecordDocument,
)

from .admin_forms import (
    AccompanyingDocumentForm, AttestationDocumentForm, BachelorMentionForm,
    BachelorTypeForm, BuildingForm, CampusForm, CancelTypeForm,
    CertificateLogoForm, CertificateSignatureForm, CourseTypeForm,
    CustomThemeFileForm, EstablishmentForm, EvaluationFormLinkForm,
    EvaluationTypeForm, FaqEntryAdminForm, GeneralBachelorTeachingForm,
    GeneralSettingsForm, HighSchoolForm, HighSchoolLevelForm, HolidayForm,
    ImmersionUserChangeForm, ImmersionUserCreationForm,
    InformationTextForm, MailTemplateForm, OffOfferEventTypeForm, PeriodForm,
    PostBachelorLevelForm, ProfileForm, PublicDocumentForm, PublicTypeForm,
    ScheduledTaskForm, StructureForm, StudentLevelForm, TrainingDomainForm,
    TrainingForm, TrainingSubdomainForm, UniversityYearForm, VacationForm,
)
from .models import (
    AccompanyingDocument, AnnualStatistics, AttestationDocument, BachelorMention,
    BachelorType, Building, Campus, CancelType, CertificateLogo, CertificateSignature,
    Course, CourseType, CustomThemeFile, Establishment, EvaluationFormLink,
    EvaluationType, FaqEntry, GeneralBachelorTeaching, GeneralSettings, HighSchool,
    HighSchoolLevel, History, Holiday, Immersion, ImmersionUser,
    InformationText, MailTemplate, OffOfferEventType, Period,
    PostBachelorLevel, Profile, PublicDocument, PublicType,
    ScheduledTask, ScheduledTaskLog, Slot, Structure, StudentLevel, Training,
    TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
)

logger = logging.getLogger(__name__)

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

        # Inject virtual apps
        for app_name, app_config in settings.ADMIN_APPS_MAPPING.items():
            new_app = app_dict[app_config['app']].copy()
            new_app['name'] = app_config['name']
            new_app['app_label'] = app_name
            app_dict[app_name] = new_app.copy()

        # This should hide apps we don't want :
        # - 'core' because all models are already grouped in virtual apps
        # - django_summernote
        app_list = sorted(
            [app for app in app_dict.values() if app['app_label'] in settings.ADMIN_APPS_ORDER],
            key=lambda x: self.find_in_list(settings.ADMIN_APPS_ORDER, x['app_label'].lower()),
        )

        for app in app_list:
            lower_app_name = app['app_label'].lower()

            if not settings.ADMIN_MODELS_ORDER.get(lower_app_name):
                app['models'].sort(key=lambda x: x.get('app_label'))
            else:
                app['models'] = list(
                    filter(
                        lambda m: m['object_name'] in settings.ADMIN_MODELS_ORDER.get(lower_app_name),
                        app['models'],
                    )
                )

                app['models'].sort(
                    key=lambda x: self.find_in_list(
                        settings.ADMIN_MODELS_ORDER[lower_app_name], x.get('object_name')
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


class HighschoolWithImmersionsListFilter(admin.SimpleListFilter):
    title = _('High schools')
    parameter_name = 'highschool'
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'

    def lookups(self, request, model_admin):
        highschools = HighSchool.objects.filter(postbac_immersion=True).order_by('city', 'label')
        return [(h.id, f"{h.city} - {h.label}") for h in highschools]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(highschool=self.value())
        else:
            return queryset


class HighschoolListFilter(admin.SimpleListFilter):
    """
    Custom filter on ref-lyc highschool or student record highschool
    """
    title = _('High schools')
    parameter_name = 'highschool'
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'

    def lookups(self, request, model_admin):
        # Optional : filter high school list by agreement value (see high school student admin filters)
        agreement_filter = {}

        if request.GET.get("agreement") and request.GET.get("agreement") in ('True', 'False'):
            agreement_filter['with_convention'] = request.GET.get("agreement") == 'True'

        highschools = HighSchool.objects.filter(**agreement_filter).order_by('city', 'label')
        return [(h.id, f"{h.city} - {h.label}") for h in highschools]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                Q(highschool=self.value())
                |Q(high_school_student_record__highschool=self.value())
            )
        else:
            return queryset


class HighschoolConventionFilter(admin.SimpleListFilter):
    title = _('Conventions')
    parameter_name = 'conventions'

    def lookups(self, request, model_admin):
        return (
            ('active', _('Active conventions')),
            ('past', _('Past conventions')),
            ('all', _('All conventions')),
            ('none', _('No conventions')),
        )

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == lookup,
                'query_string': cl.get_query_string({
                    self.parameter_name: lookup,
                }, []),
                'display': title,
            }


    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(
                convention_start_date__lte=datetime.now().date(),
                convention_end_date__gte=datetime.now().date()
            )
        elif self.value() == 'past':
            return queryset.filter(
                convention_start_date__lt=datetime.now().date(),
                convention_end_date__lt=datetime.now().date()
            )
        elif self.value() == 'all' or self.value() is None:
            return queryset

        elif self.value() == 'none':
            return queryset.filter(
                Q(convention_start_date__isnull=True, convention_end_date__isnull=True,)
            )


class StructureListFilter(admin.SimpleListFilter):
    title = _('Structures')
    parameter_name = 'structures'
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'

    def lookups(self, request, model_admin):
        structures = Structure.objects.all().order_by('establishment__code', 'label')
        return [(s.id, f"{s.establishment.code} - {s.label}" if s.establishment else s.label) for s in structures]


    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(structures=self.value())
        else:
            return queryset

class CustomUserAdmin(AdminWithRequest, UserAdmin):
    form = ImmersionUserChangeForm
    add_form = ImmersionUserCreationForm

    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_groups_list',
        'get_activated_account',
        'destruction_date',
        'last_login',
        'is_superuser',
        'is_staff',
    ]

    list_filter = (
        'is_staff',
        'is_superuser',
        ActivationFilter,
        ('groups', RelatedDropdownFilter),
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
    )

    def get_activated_account(self, obj):
        if not obj.is_superuser and (obj.is_high_school_student() or obj.is_student()):
            if obj.is_valid():
                return _('Yes')
            else:
                return _('No')
        else:
            return ''

    def get_edited_record(self, obj):
        if not obj.is_superuser and (obj.is_high_school_student() or obj.is_student() or obj.is_visitor()):
            if obj.is_high_school_student():
                record = obj.get_high_school_student_record()
            elif obj.is_student():
                record = obj.get_student_record()
            elif obj.is_visitor():
                record = obj.get_visitor_record()
            return _('Yes') if record else _('No')
        else:
            return ''

    def get_validated_record(self, obj):
        if not obj.is_superuser and (obj.is_high_school_student() or obj.is_student() or obj.is_visitor()):
            if obj.is_high_school_student():
                record = obj.get_high_school_student_record()
            elif obj.is_student():
                record = obj.get_student_record()
            elif obj.is_visitor():
                record = obj.get_visitor_record()
            return _('Yes') if record and record.is_valid() else _('No')
        else:
            return ''

    def get_establishment(self, obj):
        if obj.is_superuser:
            return ''

        if obj.is_high_school_student():
            record = obj.get_high_school_student_record()
            if record and record.highschool:
                return record.highschool
            else:
                return ''
        elif obj.is_student():
            record = obj.get_student_record()
            if record and record.institution:
                return record.institution.uai_code
        elif obj.is_structure_manager() or obj.is_structure_consultant():
            if obj.highschool:
                return obj.highschool
            elif obj.establishment:
                return obj.establishment
        elif obj.is_speaker() or obj.is_operator() or obj.is_master_establishment_manager() \
            or obj.is_establishment_manager() or obj.is_high_school_manager() or obj.is_legal_department_staff():
            if obj.highschool:
                return obj.highschool
            elif obj.establishment:
                return obj.establishment
        else:
            return ''

    def get_highschool(self, obj):
        try:
            return obj.highschool
        except:
            return ''

    def get_structure(self, obj):
        try:
            structures = ', '.join([s.label for s in obj.structures.all().order_by('label')])
            return structures
        except:
            return ''

    def get_groups_list(self, obj):
        return [group.name for group in obj.groups.all().order_by('name')]

    get_activated_account.short_description = _('Activated account')
    get_edited_record.short_description = _('Edited record')
    get_validated_record.short_description = _('Validated record')
    get_establishment.short_description = _('Establishment')
    get_groups_list.short_description = _('Groups')
    get_structure.short_description = _('Structure')
    get_highschool.short_description = _('High school')

    filter_horizontal = ('structures', 'groups', 'user_permissions')

    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('establishment', 'search', 'email', 'first_name',
                           'last_name',),
            },
        ),
    )

    high_school_manager_add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'first_name', 'last_name',),
            },
        ),
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.form.admin_site = admin_site

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Disable delete
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def get_queryset(self, request):
        # Other groups has no "Can view structure" permission
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        # Users are not allowed to modify their own account
        qs = qs.exclude(id=request.user.id)

        if request.user.is_establishment_manager():
            es = request.user.establishment
            return qs.filter(
                Q(groups__name__in=['REF-LYC', 'LYC', 'ETU', 'CONS-STR'])|Q(structures__establishment=es)|Q(establishment=es)
            ).distinct()

        if request.user.is_high_school_manager():
            return qs.filter(groups__name__in=['INTER'], highschool=request.user.highschool)

        return qs

    def has_delete_permission(self, request, obj=None):
        no_delete_msg = _("You don't have enough privileges to delete this account")

        if obj:
            if request.user.is_superuser:
                return True
            elif obj.is_superuser:
                messages.warning(request, no_delete_msg)
                return False

            if obj.courses.all().exists() or obj.visits.all().exists():
                messages.warning(
                    request,
                    _("This account is linked to courses/visits/events, you can't delete it")
                )
                return False

            user_groups = obj.groups.all().values_list('name', flat=True)

            if request.user.is_master_establishment_manager():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB-MAITRE')
                return not ({x for x in user_groups} - set(rights))

            if request.user.is_operator():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-TEC')
                return not ({x for x in user_groups} - set(rights))

            # A user can only be deleted if not superuser and the authenticated user has
            # rights on ALL his groups
            if request.user.is_establishment_manager():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB')
                establishment_condition = obj.establishment == request.user.establishment

                if not establishment_condition:
                    messages.warning(request, no_delete_msg)
                    return False

                return not ({x for x in user_groups} - set(rights))

            if request.user.is_high_school_manager():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-LYC')
                highschool_condition = obj.highschool == request.user.highschool

                if not highschool_condition:
                    messages.warning(request, no_delete_msg)
                    return False

                return not ({x for x in user_groups} - set(rights))

            messages.warning(request, no_delete_msg)

            return False

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if obj:
            if obj.is_superuser:
                return False

            # When creating a user, the group is not here yet
            if request.user.is_master_establishment_manager():
                return not obj.is_master_establishment_manager() and not obj.is_operator()

            # A user can only be updated if not superuser and the authenticated user has
            # rights on ALL his groups
            user_groups = obj.groups.all().values_list('name', flat=True)

            if request.user.is_operator():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-TEC')
                if not ({x for x in user_groups} - set(rights)):
                    return True

            if request.user.is_establishment_manager():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-ETAB')
                if not ({x for x in user_groups} - set(rights)):
                    return True

            if request.user.is_high_school_manager():
                rights = settings.HAS_RIGHTS_ON_GROUP.get('REF-LYC')
                highschool_condition = obj.highschool == request.user.highschool

                return highschool_condition and not ({x for x in user_groups} - set(rights))

            return False

        return True

    def has_add_permission(self, request):
        has_permission = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager()
        ]

        if any(has_permission):
            return True

        if request.user.is_high_school_manager():
            if request.user.highschool and request.user.highschool.postbac_immersion:
                return True

        return False

    def get_fieldsets(self, request, obj=None):
        # On user change, add structures in permissions fieldset
        # after Group selection
        if not obj:
            if not request.user.is_superuser:
                if request.user.is_high_school_manager():
                    return self.high_school_manager_add_fieldsets

            return super().get_fieldsets(request, obj)
        else:
            lst = list(UserAdmin.fieldsets)
            permissions_fields = list(lst[2])

            permissions_fields_list = list(permissions_fields[1]['fields'])
            permissions_fields_list.insert(4, 'establishment')
            permissions_fields_list.insert(5, 'structures')
            permissions_fields_list.insert(6, 'highschool')

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
        js = (
            'js/vendor/jquery/jquery-3.4.1.min.js',
            'js/immersion_user.min.js',
        )
        css = {'all': ('css/immersionlyceens.min.css',)}


class ProfileAdmin(AdminWithRequest, admin.ModelAdmin):
    form = ProfileForm
    list_display = ('code', 'label', 'active')
    list_filter = ('active',)
    ordering = ('label',)
    search_fields = ('label',)

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_operator()

    def has_delete_permission(self, request, obj=None):
        if AttestationDocument.objects.filter(profiles=obj).exists():
            messages.warning(request, _("This profile can't be deleted because it is used by an attestation document"))
            return False

        return request.user.is_superuser or request.user.is_operator()



class TrainingDomainAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingDomainForm
    list_display = ('label', 'active')
    list_filter = ('active', )

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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and Training.objects.filter(training_subdomains=obj).exists():
            messages.warning(
                request, _("""This training subdomain can't be deleted """ """because it is used by a training"""),
            )
            return False

        return True


class CampusAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CampusForm
    list_display = ('label', 'establishment', 'city', 'active')
    list_filter = (
        'active',
        ('establishment', RelatedDropdownFilter),
    )
    ordering = ('label',)
    search_fields = ('label',)

    fieldsets = (
        (None, {'fields': (
            'establishment',
            'label',
            'active',
            'department',
            'city',
            'zip_code',
            )}
        ),
    )

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.pk:
            return ('establishment', ) + self.readonly_fields
        return self.readonly_fields

    def get_queryset(self, request):
        # Other groups has no "Can view structure" permission
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if request.user.is_establishment_manager():
            return qs.filter(Q(establishment__isnull=True)|Q(establishment=request.user.establishment))

        return qs


    def has_delete_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        if not any(valid_groups):
            return False

        # establishment manager : can't delete a campus if it's not attached to his/her own establishment
        if obj and request.user.establishment and request.user.is_establishment_manager() and not \
                request.user.establishment == obj.establishment:
            return False

        if obj and Building.objects.filter(campus=obj).exists():
            messages.warning(request, _("This campus can't be deleted because it is used by a building"))
            return False

        return True

    class Media:
        if settings.USE_GEOAPI:
            js = (
                'js/jquery-3.4.1.slim.min.js',
                'js/admin_campus.min.js',
            )


class BuildingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BuildingForm
    list_display = ('label', 'campus', 'get_establishment', 'url', 'active')
    list_filter = (
        ('campus', RelatedDropdownFilter),
        ('campus__establishment', RelatedDropdownFilter),
        'active'
    )
    ordering = (
        'campus__establishment',
        'campus',
        'label',
    )
    search_fields = ('label',)

    def get_establishment(self, obj):
        return obj.campus.establishment

    get_establishment.short_description = _('Establishments')

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def get_queryset(self, request):
        # Other groups has no "Can view structure" permission
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if request.user.is_establishment_manager():
            return qs.filter(Q(campus__establishment__isnull=True)|Q(campus__establishment=request.user.establishment))

        return qs

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and Slot.objects.filter(building=obj).exists():
            messages.warning(request, _("This building can't be deleted because it is used by a slot"))
            return False

        return True

    class Media:
        js = (
            'js/jquery-3.4.1.slim.min.js',
            'js/admin_building.min.js',
        )


class BachelorTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BachelorTypeForm
    list_display = ('label', 'pre_bachelor_level', 'general', 'professional', 'technological', 'active')
    ordering = ('label',)

    def has_module_permission(self, request):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        obj_in_use = any([
            HighSchoolStudentRecord.objects.filter(Q(bachelor_type=obj) | Q(origin_bachelor_type=obj)).exists(),
            StudentRecord.objects.filter(origin_bachelor_type=obj).exists(),
        ])

        if obj and obj_in_use:
            messages.warning(
                request,
                _(
                    """This bachelor type can't be deleted """
                    """because it is used by a high school or student record"""
                ),
            )
            return False

        return True

class BachelorMentionAdmin(AdminWithRequest, admin.ModelAdmin):
    form = BachelorMentionForm
    list_display = ('label', 'active')
    ordering = ('label',)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and HighSchoolStudentRecord.objects.filter(general_bachelor_teachings=obj).exists():
            messages.warning(
                request,
                _("""This teaching can't be deleted """ """because it is used by a high-school student record"""),
            )
            return False

        return True


class EstablishmentAdmin(AdminWithRequest, admin.ModelAdmin):
    form = EstablishmentForm
    list_display = ('code', 'label', 'master', 'active', 'signed_charter')
    list_filter = ('active',)
    ordering = ('code', 'master', 'label', 'active', 'signed_charter')
    search_fields = ('label',)

    formfield_overrides = {
        JSONField: {'widget': JSONEditorWidget(options={ 'mode': 'form' })},
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


    def get_fieldsets(self, request, obj=None):
        """
        Hide some critical fields for non-authorized users (like plugin settings with passwords)
        """
        fieldset = super().get_fieldsets(request, obj)

        if not request.user.is_superuser and not request.user.is_operator():
            hidden_fields = ['data_source_settings', 'objects']
            fieldset[0][1]['fields'] = [field for field in fieldset[0][1]['fields'] if field not in hidden_fields]

        return fieldset


    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser \
               or request.user.is_operator() \
               or request.user.is_master_establishment_manager()

    def get_readonly_fields(self, request, obj=None):
        user = request.user

        if not any([user.is_master_establishment_manager(), user.is_operator(), user.is_superuser]):
            return super().get_readonly_fields(request, obj) + (
                'active', 'signed_charter', 'code', 'label', 'uai_reference', 'short_label', 'department',
                'address', 'address2', 'address3', 'city', 'zip_code', 'phone_number', 'fax', 'badge_html_color',
                'email', 'data_source_plugin', 'data_source_settings', 'logo', 'signature', 'objects',
                'certificate_header', 'certificate_footer'
            )
        elif request.user.is_master_establishment_manager() and not user.is_superuser:
            return super().get_readonly_fields(request, obj) + (
                'active', 'signed_charter', 'code', 'label', 'uai_reference', 'short_label', 'department',
                'address', 'address2', 'address3', 'city', 'zip_code', 'phone_number', 'fax', 'badge_html_color',
                'email', 'data_source_plugin', 'data_source_settings', 'objects',
            )

        return super().get_readonly_fields(request, obj)


    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser and not request.user.is_operator():
            return False

        # Test existing data before deletion (see US 160)
        if obj and Structure.objects.filter(establishment=obj).exists():
            messages.warning(request, _("This establishment can't be deleted (linked structures)"))
            return False

        return True


class StructureAdmin(AdminWithRequest, admin.ModelAdmin):
    form = StructureForm
    list_display = ('code', 'label', 'establishment', 'active', 'mailing_list')
    list_filter = (
        'active',
        ('establishment', RelatedDropdownFilter),
    )
    ordering = ('label',)
    search_fields = ('label',)

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if request.user.is_establishment_manager() and not request.user.is_superuser:
            readonly_fields.append("mailing_list")

        return readonly_fields

    def get_actions(self, request):
        # Disable delete
        actions = super().get_actions(request)
        # Manage KeyError if rights for groups don't include delete !
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    def get_queryset(self, request):
        # Other groups has no "Can view structure" permission
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        if request.user.is_establishment_manager():
            return qs.filter(Q(establishment__isnull=True)|Q(establishment=request.user.establishment))

        return qs

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        if any(valid_groups):
            return True

        if obj and request.user.is_establishment_manager() and obj.establishment == request.user.establishment:
            return True

        return False

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ]

        if not any(valid_groups):
            return False

        # Establishment manager : own establishment structures only
        if obj and request.user.is_establishment_manager() and obj.establishment != request.user.establishment:
            return False

        if obj and Training.objects.filter(structures=obj).exists():
            messages.warning(request, _("This structure can't be deleted because it is used by a training"))
            return False

        return True


class TrainingAdmin(AdminWithRequest, admin.ModelAdmin):
    form = TrainingForm
    filter_horizontal = ('structures', 'training_subdomains')
    list_display = ('label', 'get_structures_list', 'highschool', 'get_subdomains_list', 'active')

    list_filter = (
        'active',
        ('structures__establishment', RelatedDropdownFilter),
        StructureListFilter,
        HighschoolWithImmersionsListFilter,
        ('training_subdomains', RelatedDropdownFilter),
    )

    ordering = ('label',)
    search_fields = ('label',)

    def get_structures_list(self, obj):
        return ["{} ({})".format(s.code, s.establishment.code if s.establishment else '-')
            for s in obj.structures.all().order_by('code')
        ]

    get_structures_list.short_description = _('Structures')

    def get_subdomains_list(self, obj):
        return [sub.label for sub in obj.training_subdomains.all().order_by('label')]

    get_structures_list.short_description = _('Structures')
    get_subdomains_list.short_description = _('Training subdomains')

    def get_queryset(self, request):
        # Other groups has no "Can view structure" permission
        qs = super().get_queryset(request)

        if request.user.is_master_establishment_manager():
            return qs

        if request.user.is_establishment_manager():
            return qs.filter(structures__establishment=request.user.establishment).distinct()

        return qs

    def has_delete_permission(self, request, obj=None):
        user_conditions = [
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ]

        if not any(user_conditions):
            return False

        if obj and Course.objects.filter(training=obj).exists():
            messages.warning(
                request, _("This training can't be deleted because it is used by some courses"),
            )
            return False

        return True


class CancelTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CancelTypeForm
    list_display = ('code', 'label', 'active', 'system')
    list_display_links = ('code', 'label', )
    ordering = ('label',)

    def has_change_permission(self, request, obj=None):
        if not obj:
            return any([
                request.user.is_superuser,
                request.user.is_master_establishment_manager(),
                request.user.is_operator(),
            ])
        else:
            # In use
            if Immersion.objects.filter(cancellation_type=obj).exists():
                messages.warning(
                    request, _("This cancellation type can't be updated because it is used by some registrations"),
                )
                return False
            # Protected
            elif obj.system and not request.user.is_operator() and not request.user.is_superuser:
                return False
            # Not allowed
            elif not request.user.is_master_establishment_manager() and not request.user.is_operator():
                return False

        return True

    def has_delete_permission(self, request, obj=None):
        if not obj:
            return any([
                request.user.is_superuser,
                request.user.is_master_establishment_manager(),
                request.user.is_operator(),
            ])
        else:
            # Protected types
            if obj.system and not request.user.is_operator() and not request.user.is_superuser:
                return False

            if not request.user.is_master_establishment_manager() and not request.user.is_operator():
                return False

            if Immersion.objects.filter(cancellation_type=obj).exists():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and AccompanyingDocument.objects.filter(public_type=obj).exists():
            messages.warning(
                request,
                _("""This public type can't be deleted """ """because it is used by accompanying document(s)"""),
            )
            return False

        return True


class HolidayAdmin(AdminWithRequest, admin.ModelAdmin):

    form = HolidayForm
    list_display = ('label', 'date')
    ordering = ('date',)

    def has_delete_permission(self, request, obj=None):
        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)

        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # The current active year has already started
        if now >= univ_year.start_date:
            return False

        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)

        # No active year
        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # The current active year has already started
        if now >= univ_year.start_date:
            return False

        return True

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser or request.user.is_master_establishment_manager():
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)

        # No active year
        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # The current active year has already started
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

        # No active year
        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # Active year has already started
        if now >= univ_year.start_date:
            return False

        return True

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)

        # No active year
        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # Active year has already started
        if now >= univ_year.start_date:
            return False

        return True

    def has_add_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        now = datetime.now().date()
        univ_years = UniversityYear.objects.filter(active=True)

        # No active year
        if not univ_years.exists():
            return True

        univ_year = univ_years[0]

        # Active year has already started
        if now >= univ_year.start_date:
            return False

        return True


class UniversityYearAdmin(AdminWithRequest, admin.ModelAdmin):
    change_list_template = "admin/core/universityyear/change_list.html"
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
        elif request.user.is_master_establishment_manager() or request.user.is_operator():
            return not (UniversityYear.objects.filter(purge_date__isnull=True).count() > 0)
        else:
            return False

    def has_delete_permission(self, request, obj=None):

        if request.user.is_superuser:
            return True
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj:
            if obj.start_date <= datetime.today().date() <= obj.end_date:
                messages.warning(
                    request,
                    _("""This university year can't be deleted """
                      """because university year has already started"""),
                )
                return False
            elif obj.purge_date is not None:
                messages.warning(request, _("This university year can't be deleted because a purge date is defined"))
                return False

        return True

    class Media:
        js = (
            "js/vendor/jquery/jquery-3.4.1.min.js",
            "js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.js",
            "js/admin/annual_purge.js",
        )
        css = {
            "all": (
                "js/vendor/jquery-ui/jquery-ui-1.12.1/jquery-ui.min.css",
                "css/admin_university_year.css",
            )
        }


class PeriodAdmin(AdminWithRequest, admin.ModelAdmin):
    """
    Period admin class
    """
    form = PeriodForm
    list_display = (
        'label', 'registration_start_date', 'immersion_start_date', 'immersion_end_date', 'allowed_immersions'
    )
    search_fields = ('label',)
    order = ('immersion_start_date', )

    def get_readonly_fields(self, request, obj=None):
        today = timezone.localdate()

        if not obj:
            return []

        fields = []
        uy = None

        try:
            uy = UniversityYear.get_active()
        except Exception as e:
            messages.error(
                request, _("Multiple active years found. Please check your university years settings."),
            )

        if uy is None or request.user.is_superuser:
            return []

        # passed period : can't modify
        if obj.immersion_end_date < today:
            fields = [
                'label',
                'immersion_start_date',
                'immersion_end_date',
                'registration_start_date',
                'allowed_immersions',
            ]
        elif obj.registration_start_date < today < obj.immersion_end_date:
            fields = [
                'label',
                'immersion_start_date',
                'registration_start_date',
            ]

        return list(set(fields))

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_add_permission(self, request):
        uy = None

        valid_users = [
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_superuser
        ]

        try:
            uy = UniversityYear.get_active()
        except Exception as e:
            messages.error(
                request, _("Multiple active years found. Please check your university years settings."),
            )
            return False

        if not uy:
            messages.error(
                request, _("Active year not found. Please check your university years settings."),
            )
            return False

        return any(valid_users)


    def has_delete_permission(self, request, obj=None):
        today = timezone.localdate()

        if not obj:
            return False

        valid_users = [
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_superuser
        ]

        if not any(valid_users):
            messages.warning(request, _("You are not allowed to delete periods"))
            return False

        try:
            uy = UniversityYear.get_active()
        except Exception as e:
            messages.error(
                request, _("Multiple active years found. Please check your university years settings."),
            )
            return False

        if not uy:
            messages.error(
                request, _("Active year not found. Please check your university years settings."),
            )
            return False

        # University year not begun | period registration date is in the future
        year_condition = [
            uy.start_date > today,
            today < uy.end_date,
            obj.immersion_start_date > today,
        ]

        slots_exist = Slot.objects.filter(
            date__gte=obj.immersion_start_date, date__lte=obj.immersion_end_date
        ).exists()

        can_delete = not slots_exist and any(year_condition)

        if not can_delete:
            messages.warning(
                request,
                _("This period has slots or has already begun, it can't be deleted")
            )

        return can_delete


    def has_change_permission(self, request, obj=None):
        today = timezone.localdate()
        self.details = {
            'ERROR': set(),
            'WARNING': set()
        }

        if not obj:
            return False

        valid_users = [
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_superuser
        ]

        if not any(valid_users):
            self.details['WARNING'].add(_("You are not allowed to update periods"))
            return False

        try:
            uy = UniversityYear.get_active()
        except Exception as e:
            self.details['ERROR'].add(
                _("Multiple active years found. Please check your university years settings.")
            )
            return False

        if not uy:
            self.details['ERROR'].add(
                _("Active year not found. Please check your university years settings.")
            )
            return False

        # University year not begun | period registration date is in the future
        year_condition = [
            uy.start_date > today,
            today < uy.end_date,
            obj.immersion_start_date > today,
        ]

        slots_exist = Slot.objects.filter(
            date__gte=obj.immersion_start_date, date__lte=obj.immersion_end_date
        ).exists()

        can_update = not slots_exist and any(year_condition)

        if not can_update:
            self.details['WARNING'].add(
                _("This period has slots or has already begun, it can't be updated")
            )

        return can_update

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        # set error and warning messages
        try:
            obj = Period.objects.get(pk=object_id)
        except Period.DoesNotExist:
            obj = None

        self.has_change_permission(request, obj=obj)

        if hasattr(self, "details") and isinstance(self.details, dict):
            for level, message_set in  self.details.items():
                for message in message_set:
                    self.message_user(request, message, getattr(messages, level))

        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )


class HighSchoolAdmin(AdminWithRequest, admin.ModelAdmin):
    form = HighSchoolForm
    list_display = (
        'label',
        'city',
        'country',
        'email',
        'head_teacher_name',
        'referents_list',
        'with_convention',
        'custom_convention_dates',
        'active',
        'custom_postbac_immersion',
        'signed_charter',
    )
    list_filter = (
        'active',
        'postbac_immersion',
        'with_convention',
        ('country', DropdownFilter),
        ('city', DropdownFilter),
        HighschoolConventionFilter,
    )

    # Keep the list here to maintain order even when some fields are readonly
    fields = (
        'active', 'postbac_immersion', 'label', 'country', 'address', 'address2', 'address3',
        'department', 'zip_code', 'city', 'phone_number', 'fax', 'email', 'head_teacher_name',
        'with_convention', 'convention_start_date', 'convention_end_date', 'signed_charter',
        'mailing_list', 'badge_html_color', 'logo', 'signature', 'certificate_header',
        'certificate_footer'
    )

    @admin.display(description=_('Postbac immersions'), boolean=True)
    def custom_postbac_immersion(self, obj):
        return obj.postbac_immersion

    @admin.display(description=_('Convention'))
    def custom_convention_dates(self, obj):
        if obj.convention_start_date and obj.convention_end_date:
            return format_html("<br />".join(
                [_("From %s") % obj.convention_start_date, _("to %s") % str(obj.convention_end_date)]
            ))

        return ""

    ordering = ('label',)
    search_fields = ('label', 'city', 'head_teacher_name')

    def referents_list(self, obj):
        return format_html("<br />".join([
            f"{user.last_name} {user.first_name}"
            for user in obj.users.prefetch_related("groups")\
                .filter(groups__name='REF-LYC')\
                .order_by('last_name', 'first_name')
        ]))

    referents_list.short_description = _('Referents')

    def get_readonly_fields(self, request, obj=None):
        fields = []
        if obj:
            if obj.student_records.exists():
                fields.append('active')

        return fields

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
        # TODO: maybe only use model groups rights !!! => not enough :)
        conditions = [
            request.user.is_superuser or request.user.is_operator(),
            not ImmersionUser.objects.filter(highschool=obj).exists(),
            not HighSchoolStudentRecord.objects.filter(highschool=obj).exists(),
        ]

        return all(conditions)

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


    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        return True


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
                        reverse(f'admin:{doc._meta.app_label}_{doc._meta.model_name}_change', args=(doc.pk,)),
                        doc.label,
                    )
                    for doc in docs
                ),
            )

        file_url.short_description = _('Address')
        doc_used_in.short_description = _('Used in')

        return ('label', file_url, doc_used_in, 'active', 'published')

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj:
            if obj.published:
                messages.warning(
                    request, _("This document is used in public interface : deletion not allowed "),
                )
                return False

        return True


class AttestationDocumentAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):
    form = AttestationDocumentForm
    search_fields = ('label',)
    list_filter = ('active', 'mandatory', 'for_minors', 'requires_validity_date')
    list_display = ('label', 'order', 'profile_list', 'file_url', 'active', 'mandatory', 'for_minors',
                    'requires_validity_date')
    list_display_links = ('label', )
    filter_horizontal = ('profiles',)
    ordering = ('order',)
    sortable_by = ('order',)

    def changelist_view(self, request, extra_context=None):
        # access the request object when in the list view
        self.request = request
        return super().changelist_view(request, extra_context=extra_context)

    def profile_list(self, obj):
        return format_html("<br>".join([p.code for p in obj.profiles.all()]))

    def file_url(self, obj):
        if obj.template:
            url = self.request.build_absolute_uri(reverse('attestation_document', args=(obj.pk,)))
            return format_html(f'<a href="{url}">{url}</a>')

        return ""

    profile_list.short_description = _('Profiles')
    file_url.short_description = _('Address')

    def has_add_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_delete_permission(self, request, obj=None):
        hs_records = HighSchoolStudentRecordDocument.objects.filter(attestation=obj)
        visitor_records = VisitorRecordDocument.objects.filter(attestation=obj)

        if hs_records.exists() or visitor_records.exists():
            messages.warning(request, _("This attestation can't be deleted because it is used by some records"))
            return False

        return request.user.is_master_establishment_manager() or request.user.is_operator()

    class Media:
        css = {'all': ('css/immersionlyceens.min.css',)}


class MailTemplateAdmin(AdminWithRequest, SummernoteModelAdmin):
    form = MailTemplateForm
    list_display = ('code', 'label', 'active')
    filter_horizontal = ('available_vars',)
    ordering = ('code', )
    summernote_fields = ('body',)

    def has_module_permission(self, request):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_add_permission(self, request):
        # Only a superuser can add a template
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        # Only a superuser can delete a template
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

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
            # 'js/immersion_mail_templates.min.js',
            'js/immersion_mail_templates.js',
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

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [
                'evaluation_type',
            ]
        return self.readonly_fields


class GeneralSettingsAdmin(AdminWithRequest, admin.ModelAdmin):
    def setting_type(self, obj):
        if 'type' not in obj.parameters:
            return ""

        if obj.parameters['type'] == 'boolean':
            return _('boolean')
        elif obj.parameters['type'] == 'text':
            return _('text')
        elif obj.parameters['type'] == 'integer':
            return _('integer')
        else:
            #TODO: hope to have localized type in i18n files ?
            return _(obj.parameters['type'])

    def setting_value(self, obj):
        if 'type' not in obj.parameters:
            return None

        if obj.parameters['type'] == 'boolean':
            return _('Yes') if obj.parameters['value'] == True else _('No')
        else:
            return obj.parameters['value']

    def setting_description(self, obj):
        return obj.parameters.get('description', '')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return any([
            request.user.is_superuser,
            request.user.is_operator()
        ])

    def has_view_permission(self, request, obj=None):
        return any([
            request.user.is_superuser,
            request.user.is_operator()
        ])

    def has_change_permission(self, request, obj=None):
        return any([
            request.user.is_superuser,
            request.user.is_operator()
        ])

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


    form = GeneralSettingsForm
    list_display = ('setting', 'setting_value', 'setting_type', 'setting_description')
    ordering = ('setting',)

    formfield_overrides = {
        JSONField: {
            'widget': JSONEditorWidget(options={ 'mode': 'form' }),
        },
    }

    setting_type.short_description = _('Setting type')
    setting_value.short_description = _('Setting value')
    setting_description.short_description = _('Setting description')


class AnnualStatisticsAdmin(admin.ModelAdmin):
    list_display_links = None
    list_display = (
        'year',
        'platform_registrations',
        'one_immersion_registrations',
        'multiple_immersions_registrations',
        'no_course_immersions_registrations',
        'participants_one_immersion',
        'participants_multiple_immersions',
        'immersion_registrations',
        'immersion_participations',
        'immersion_participation_ratio',
        'structures_count',
        'active_trainings_count',
        'trainings_one_slot_count',
        'active_courses_count',
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

    def has_change_permission(self, request, obj=None):
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

    def has_add_permission(self, request):
        return not CertificateLogo.objects.exists()


class CertificateSignatureAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CertificateSignatureForm

    def show_signature(self, obj):
        return format_html(f'<img src="{obj.signature.url}">')

    list_display = [
        'show_signature',
    ]

    show_signature.short_description = _('Certificate signature')

    def has_add_permission(self, request):
        return not CertificateSignature.objects.exists()


class OffOfferEventTypeAdmin(AdminWithRequest, admin.ModelAdmin):
    form = OffOfferEventTypeForm
    list_display = ('label', 'active')
    ordering = ('label',)

    def has_add_permission(self, request):
        return any([request.user.is_master_establishment_manager(), request.user.is_operator()])

    def has_module_permission(self, request):
        return any([
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ])

    def has_view_permission(self, request, obj=None):
        return any([
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager(),
            request.user.is_operator()
        ])

    def has_change_permission(self, request, obj=None):
        return any([
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ])

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and not obj.can_delete():
            messages.warning(
                request,
                _("This event type is used by and event, it cannot be deleted")
            )
            return False

        return True


class HighSchoolLevelAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):
    form = HighSchoolLevelForm
    list_display = ('id', 'order', 'label', 'is_post_bachelor', 'requires_bachelor_speciality', 'active')
    ordering = ('order', )
    sortable_by = ('order', )

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_view_permission(self, request, obj=None):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_superuser
        ]
        return any(valid_groups)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False

        if obj and not obj.can_delete():
            return False

        return True

    class Media:
        css = {'all': ('css/immersionlyceens.min.css',)}


class PostBachelorLevelAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):
    form = PostBachelorLevelForm
    list_display = ('id', 'order', 'label', 'active')
    ordering = ('order', )
    sortable_by = ('order',)

    def has_add_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_module_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_view_permission(self, request, obj=None):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_superuser
        ]
        return any(valid_groups)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and not obj.can_delete():
            return False

        return True

    class Media:
        css = {'all': ('css/immersionlyceens.min.css',)}


class StudentLevelAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):
    form = StudentLevelForm
    list_display = ('id', 'order', 'label', 'active')
    ordering = ('order', )
    sortable_by = ('order',)

    def has_add_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_module_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_view_permission(self, request, obj=None):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_superuser
        ]
        return any(valid_groups)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        if obj and not obj.can_delete():
            return False

        return True

    class Media:
        css = {'all': ('css/immersionlyceens.min.css',)}


class TokenCustomAdmin(TokenAdmin, AdminWithRequest):
    def custom_has_something_permission(self, request, obj=None):
        if request.user.is_operator:
            return True
        return super().has_add_permission(request)

    def has_module_permission(self, request):
        return self.custom_has_something_permission(request)

    def has_view_permission(self, request, obj=None):
        return self.custom_has_something_permission(request, obj)

    def has_add_permission(self, request):
        return self.custom_has_something_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.custom_has_something_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.custom_has_something_permission(request, obj)


class CustomThemeFileAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CustomThemeFileForm

    def get_list_display(self, request):
        def copy_link_btn(obj):
            url = request.build_absolute_uri(obj.file.url)
            label = _('Copy file link')
            return format_html(f"""
                <a href="#" class="btn btn-secondary mb-1" onclick="navigator.clipboard.writeText('{url}')">
                <i class="fa fas fa-copy" data-toggle="tooltip" title="{label}"></i>

                </a>
                """
            )


        copy_link_btn.short_description = _('Copy file link')
        return ('type', 'file', copy_link_btn, )


    def has_add_permission(self, request):
        return request.user.is_operator() or request.user.is_superuser

    def has_module_permission(self, request):
        return request.user.is_operator() or request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_operator() or request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_operator() or request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_operator() or request.user.is_superuser

    class Media:
        css = {
             'all': ('fonts/fontawesome/4.7.0/css/font-awesome.min.css',)
        }


class FaqEntryAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):

    form = FaqEntryAdminForm
    list_display = ('id', 'order', 'label', 'question', 'active')
    ordering = ('order', )
    sortable_by = ('order', )

    def has_add_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_module_permission(self, request):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_view_permission(self, request, obj=None):
        return request.user.is_master_establishment_manager() or request.user.is_operator()

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_superuser
        ]
        return any(valid_groups)

    def has_delete_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_superuser
        ]
        return any(valid_groups)

    class Media:
        css = {'all': ('css/immersionlyceens.min.css',)}


class ScheduledTaskAdmin(AdminWithRequest, admin.ModelAdmin):
    form = ScheduledTaskForm
    list_display = ('command_name', 'description', 'date', 'time', 'frequency', 'days', 'active')
    ordering = ('command_name', 'time', )
    list_filter = ('active', )

    fieldsets = (
        (None, {'fields': (
            'command_name',
            'description',
            'active',
            'date',
            'time',
            'frequency',
            'monday',
            'tuesday',
            'wednesday',
            'thursday',
            'friday',
            'saturday',
            'sunday')}
         ),
    )

    def days(self, obj):
        week_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        days = ", ".join(map(lambda d:gettext(d.title()), filter(lambda day:getattr(obj, day) is True, week_days)))

        return days

    days.short_description = _('Days')

    def get_readonly_fields(self, request, obj=None):
        user = request.user

        if not user.is_superuser:
            return super().get_readonly_fields(request, obj) + ('command_name', 'description')

        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.is_operator()

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser


class ScheduledTaskLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'execution_date', 'success', 'message')
    ordering = ('-execution_date', )
    list_filter = ('task', 'success')

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True


class HistoryAdmin(admin.ModelAdmin):
    list_display = ('date', 'action', 'username', 'user', 'hijacked', 'ip')
    list_filter = ('action', )
    ordering = ('-date',)

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


admin.site.unregister(TokenProxy)
admin.site.register(TokenProxy, TokenCustomAdmin)

admin.site = CustomAdminSite(name='Repositories')

admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(Profile, ProfileAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Establishment, EstablishmentAdmin)
admin.site.register(Structure, StructureAdmin)
admin.site.register(BachelorType, BachelorTypeAdmin)
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
admin.site.register(Period, PeriodAdmin)
admin.site.register(MailTemplate, MailTemplateAdmin)
admin.site.register(InformationText, InformationTextAdmin)
admin.site.register(AccompanyingDocument, AccompanyingDocumentAdmin)
admin.site.register(PublicDocument, PublicDocumentAdmin)
admin.site.register(AttestationDocument, AttestationDocumentAdmin)
admin.site.register(EvaluationFormLink, EvaluationFormLinkAdmin)
admin.site.register(EvaluationType, EvaluationTypeAdmin)
admin.site.register(GeneralSettings, GeneralSettingsAdmin)
admin.site.register(AnnualStatistics, AnnualStatisticsAdmin)
admin.site.register(CertificateLogo, CertificateLogoAdmin)
admin.site.register(CertificateSignature, CertificateSignatureAdmin)
admin.site.register(OffOfferEventType, OffOfferEventTypeAdmin)
admin.site.register(HighSchoolLevel, HighSchoolLevelAdmin)
admin.site.register(PostBachelorLevel, PostBachelorLevelAdmin)
admin.site.register(StudentLevel, StudentLevelAdmin)
admin.site.register(CustomThemeFile, CustomThemeFileAdmin)
admin.site.register(FaqEntry, FaqEntryAdmin)
admin.site.register(ScheduledTask, ScheduledTaskAdmin)
admin.site.register(ScheduledTaskLog, ScheduledTaskLogAdmin)
admin.site.register(History, HistoryAdmin)
