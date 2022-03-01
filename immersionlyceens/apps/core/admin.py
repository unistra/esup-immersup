from datetime import datetime

from adminsortable2.admin import SortableAdminMixin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import JSONField, Q
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, RelatedDropdownFilter,
)
from django_json_widget.widgets import JSONEditorWidget
from django_summernote.admin import SummernoteModelAdmin

from .admin_forms import (
    AccompanyingDocumentForm, BachelorMentionForm, BuildingForm, CalendarForm,
    CampusForm, CancelTypeForm, CertificateLogoForm, CertificateSignatureForm,
    CourseTypeForm, EstablishmentForm, EvaluationFormLinkForm,
    EvaluationTypeForm, GeneralBachelorTeachingForm, GeneralSettingsForm,
    HighSchoolForm, HighSchoolLevelForm, HolidayForm, ImmersionUserChangeForm,
    ImmersionUserCreationForm, InformationTextForm, MailTemplateForm,
    OffOfferEventTypeForm, PostBachelorLevelForm, PublicDocumentForm,
    PublicTypeForm, StructureForm, StudentLevelForm, TrainingDomainForm,
    TrainingForm, TrainingSubdomainForm, UniversityYearForm, VacationForm,
)
from .models import (
    AccompanyingDocument, AnnualStatistics, BachelorMention, Building,
    Calendar, Campus, CancelType, CertificateLogo, CertificateSignature,
    Course, CourseType, Establishment, EvaluationFormLink, EvaluationType,
    GeneralBachelorTeaching, GeneralSettings, HighSchool, HighSchoolLevel,
    Holiday, Immersion, ImmersionUser, InformationText, MailTemplate,
    OffOfferEventType, PostBachelorLevel, PublicDocument, PublicType, Slot,
    Structure, StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UniversityYear, Vacation,
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
    title = _('High schools')
    parameter_name = 'highschool'
    template = 'django_admin_listfilter_dropdown/dropdown_filter.html'

    def lookups(self, request, model_admin):
        highschools = HighSchool.objects.all().order_by('city', 'label')
        return [(h.id, f"{h.city} - {h.label}") for h in highschools]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(highschool=self.value())
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
        if self.value() == 'active' or self.value() == None:
            return queryset.filter(
                convention_start_date__lte=datetime.now().date(),
                convention_end_date__gte=datetime.now().date()
            )
        elif self.value() == 'past':
            return queryset.filter(
                convention_start_date__lt=datetime.now().date(),
                convention_end_date__lt=datetime.now().date()
            )
        elif self.value() == 'all':
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
            return record.home_institution()[0]
        elif obj.is_structure_manager():
            structures = ', '.join([s.label for s in obj.structures.all().order_by('label')])
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
                'fields': ('establishment', 'search', 'username', 'password1', 'password2', 'email', 'first_name',
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
                Q(groups__name__in=['REF-LYC', 'LYC', 'ETU'])|Q(structures__establishment=es)|Q(establishment=es)
            )

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
                return not obj.is_master_establishment_manager()

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
    list_display = ('label', 'establishment', 'active')
    list_filter = (
        'active',
        ('establishment', RelatedDropdownFilter),
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

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser \
               or request.user.is_operator() \
               or request.user.is_master_establishment_manager()

    def get_readonly_fields(self, request, obj=None):
        user = request.user

        if not any([user.is_master_establishment_manager(), user.is_operator(), user.is_superuser]):
            return super().get_readonly_fields(request, obj) + (
                'code', 'label', 'short_label', 'department', 'city', 'zip_code', 'phone_number', 'fax',
                'badge_html_color', 'email', 'data_source_plugin',
                'data_source_settings', 'logo', 'signature', 'objects', 'activated',
                'address', 'address2', 'address3', 'certificate_header', 'certificate_footer'
            )
        elif request.user.is_master_establishment_manager() and not user.is_superuser:
            return super().get_readonly_fields(request, obj) + (
                'code', 'label', 'short_label', 'department', 'city', 'zip_code', 'phone_number', 'fax',
                'badge_html_color', 'email', 'data_source_plugin',
                'data_source_settings', 'objects', 'activated',
                'address', 'address2', 'address3'
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
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
        if not request.user.is_master_establishment_manager() and not request.user.is_operator():
            return False

        # Only one calendar can exist
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
        'postbac_immersion',
        'signed_charter',
    )
    list_filter = (
        'postbac_immersion',
        ('city', DropdownFilter),
        HighschoolConventionFilter,
    )

    ordering = ('label',)
    search_fields = ('label', 'city', 'head_teacher_name')

    def referents_list(self, obj):
        return [
            f"{user.last_name} {user.first_name}"
            for user in obj.highschool_referent.filter(groups__name='REF-LYC').order_by('last_name', 'first_name')
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


class MailTemplateAdmin(AdminWithRequest, SummernoteModelAdmin):
    form = MailTemplateForm
    list_display = ('code', 'label', 'active')
    filter_horizontal = ('available_vars',)
    summernote_fields = ('body',)

    def has_module_permission(self, request):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
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


class CertificateSignatureAdmin(AdminWithRequest, admin.ModelAdmin):
    form = CertificateSignatureForm

    def show_signature(self, obj):
        return format_html(f'<img src="{obj.signature.url}">')

    list_display = [
        'show_signature',
    ]

    show_signature.short_description = _('Certificate signature')


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
            return False

        return True


class HighSchoolLevelAdmin(AdminWithRequest, SortableAdminMixin, admin.ModelAdmin):
    form = HighSchoolLevelForm
    list_display = ('id', 'order', 'label', 'is_post_bachelor', 'active')
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


admin.site = CustomAdminSite(name='Repositories')

admin.site.register(ImmersionUser, CustomUserAdmin)
admin.site.register(TrainingDomain, TrainingDomainAdmin)
admin.site.register(TrainingSubdomain, TrainingSubdomainAdmin)
admin.site.register(Training, TrainingAdmin)
admin.site.register(Establishment, EstablishmentAdmin)
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
admin.site.register(OffOfferEventType, OffOfferEventTypeAdmin)
admin.site.register(HighSchoolLevel, HighSchoolLevelAdmin)
admin.site.register(PostBachelorLevel, PostBachelorLevelAdmin)
admin.site.register(StudentLevel, StudentLevelAdmin)
