from django.contrib import admin, messages
from django.db.models import JSONField, Q
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, RelatedDropdownFilter,
)
from hijack.contrib.admin import HijackUserAdminMixin

from immersionlyceens.apps.core.admin import (
    ActivationFilter, AdminWithRequest, CustomUserAdmin, HighschoolListFilter,
)
from immersionlyceens.apps.core.admin_forms import ImmersionUserGroupForm
from immersionlyceens.apps.core.models import ImmersionUser
from immersionlyceens.apps.immersion.models import (
    HighSchoolStudentRecord, StudentRecord, VisitorRecord,
)

from .models import (
    EstablishmentManager, HighSchoolManager, HighSchoolStudent,
    LegalDepartmentStaff, MasterEstablishmentManager, Operator, Speaker,
    StructureConsultant, StructureManager, Student, UserGroup, Visitor,
)


class ValidRecordFilter(admin.SimpleListFilter):
    title = _('Validated record')
    parameter_name = 'get_validated_record'

    def lookups(self, request, model_admin):
        return [('True', _('Yes')), ('False', _('No'))]

    def queryset(self, request, queryset):
        value = self.value()
        # TODO: maybe better way to do this ?
        hr = HighSchoolStudentRecord.objects.filter(validation=2).values_list('student__id', flat=True)
        sr = StudentRecord.objects.all().values_list('student__id', flat=True)
        vr = VisitorRecord.objects.filter(validation=2).values_list('visitor__id', flat=True)
        q_filter = (Q(id__in=hr) | Q(id__in=sr) | Q(id__in=vr))
        if value == 'True':
            return queryset.filter(q_filter)
        elif value == 'False':
            return queryset.exclude(q_filter)
        return queryset

class AgreementHighSchoolFilter(admin.SimpleListFilter):
    title = _('High school agreement')
    parameter_name = 'agreement'

    def lookups(self, request, model_admin):
        return [('True', _('Yes')), ('False', _('No'))]

    def queryset(self, request, queryset):
        value = self.value()
        if value in ('True', 'False'):
            return queryset\
                .prefetch_related("high_school_student_record__highschool")\
                .filter(high_school_student_record__highschool__with_convention=(value == 'True'))

        return queryset


class HighschoolStudentAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'get_activated_account',
        'destruction_date',
        'get_edited_record',
        'get_validated_record',
        'last_login',
    ]

    list_filter = (
        ActivationFilter,
        ValidRecordFilter,
        AgreementHighSchoolFilter,
        HighschoolListFilter,
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='LYC').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class StudentAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'get_activated_account',
        'destruction_date',
        'get_edited_record',
        'get_validated_record',
        'last_login',
    ]

    list_filter = (
        ActivationFilter,
        ValidRecordFilter,
        ('establishment', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='ETU').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class VisitorAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'destruction_date',
        'get_edited_record',
        'get_validated_record',
        'last_login',
    ]

    list_filter = (ValidRecordFilter, )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='VIS').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class SpeakerAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
    )

    def get_queryset(self, request):
        Q_filter = Q()

        if request.user.is_establishment_manager():
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter, groups__name='INTER',).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator(),
            request.user.is_establishment_manager(),
        ]
        return any(valid_groups)


class OperatorAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='REF-TEC').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_module_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)


class EstablishmentManagerAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        Q_filter = Q()

        if request.user.is_establishment_manager():
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter, groups__name='REF-ETAB',).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class MasterEstablishmentManagerAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='REF-ETAB-MAITRE').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)

    def has_module_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_master_establishment_manager(),
            request.user.is_operator()
        ]

        return any(valid_groups)


class HighSchoolManagerAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_highschool',
        'last_login',
    ]

    list_filter = (
        HighschoolListFilter,
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='REF-LYC').order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class StructureManagerAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'get_structure',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        ('structures', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        filter = {}
        Q_filter = Q()

        if request.user.is_high_school_manager() and request.user.highschool:
            filter = {'highschool' : 'request.user.highschool'}

        if request.user.is_establishment_manager() and not request.user.is_superuser:
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter,
                                            groups__name='REF-STR',
                                            **filter).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)

    def has_change_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)


class LegalDepartmentStaffAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        filter = {}
        Q_filter = Q()

        if request.user.is_high_school_manager() and request.user.highschool:
            filter = {'highschool' : 'request.user.highschool'}

        if request.user.is_establishment_manager():
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter,
                                            groups__name='SRV-JUR',
                                            **filter).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)

    def has_change_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)


class ImmersionUserGroupAdmin(AdminWithRequest, admin.ModelAdmin):
    form = ImmersionUserGroupForm
    list_display = ('id', 'get_immersionusers')
    filter_horizontal = ('immersionusers', )

    def get_immersionusers(self, obj):
        return format_html("<br>".join([f"{user} ({user.email})" for user in obj.immersionusers.all()]))

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
        return request.user.is_superuser or request.user.is_operator()

    def has_delete_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
        ]

        return any(valid_groups)

    def has_change_permission(self, request, obj=None):
        valid_groups = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
        ]

        return any(valid_groups)

    get_immersionusers.short_description = _('Linked users')
    get_immersionusers.allow_tags = True


class StructureConsultantAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
        'get_structure',
        'last_login',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        ('structures', RelatedDropdownFilter),
    )

    def get_queryset(self, request):
        filter = {}
        Q_filter = Q()

        if request.user.is_high_school_manager() and request.user.highschool:
            filter = {'highschool' : 'request.user.highschool'}

        if request.user.is_establishment_manager() and not request.user.is_superuser:
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter,
                                            groups__name='CONS-STR',
                                            **filter).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)

    def has_change_permission(self, request, obj=None):
        conditions = [
            request.user.is_superuser,
            request.user.is_operator(),
            request.user.is_master_establishment_manager(),
            request.user.is_establishment_manager() and obj and
                obj.structures.all().intersection(request.user.get_authorized_structures()).exists(),
        ]

        return any(conditions)


admin.site.register(HighSchoolStudent, HighschoolStudentAdmin)
admin.site.register(Student, StudentAdmin)
admin.site.register(Visitor, VisitorAdmin)
admin.site.register(Speaker, SpeakerAdmin)
admin.site.register(Operator, OperatorAdmin)
admin.site.register(MasterEstablishmentManager, MasterEstablishmentManagerAdmin)
admin.site.register(EstablishmentManager, EstablishmentManagerAdmin)
admin.site.register(StructureManager, StructureManagerAdmin)
admin.site.register(HighSchoolManager, HighSchoolManagerAdmin)
admin.site.register(LegalDepartmentStaff, LegalDepartmentStaffAdmin)
admin.site.register(UserGroup, ImmersionUserGroupAdmin)
admin.site.register(StructureConsultant, StructureConsultantAdmin)
