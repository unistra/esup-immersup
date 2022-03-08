from datetime import datetime

from adminsortable2.admin import SortableAdminMixin
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.actions import (
    delete_selected, delete_selected as default_delete_selected,
)
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import JSONField, Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.encoding import force_text
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, ugettext_lazy as _
from django_admin_listfilter_dropdown.filters import (
    DropdownFilter, RelatedDropdownFilter,
)
from django_json_widget.widgets import JSONEditorWidget
from django_summernote.admin import SummernoteModelAdmin
from hijack.contrib.admin import HijackUserAdminMixin
from immersionlyceens.apps.core.admin import (
    ActivationFilter, AdminWithRequest, CustomUserAdmin, HighschoolListFilter,
)
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, AnnualStatistics, BachelorMention, Building,
    Calendar, Campus, CancelType, CertificateLogo, CertificateSignature,
    Course, CourseType, Establishment, EvaluationFormLink, EvaluationType,
    GeneralBachelorTeaching, GeneralSettings, HighSchool, HighSchoolLevel,
    Holiday, Immersion, ImmersionUser, InformationText, MailTemplate,
    OffOfferEventType, PostBachelorLevel, PublicDocument, PublicType, Slot,
    Structure, StudentLevel, Training, TrainingDomain, TrainingSubdomain,
    UniversityYear, Vacation,
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord

from .models import (
    EstablishmentManager, HighSchoolManager, HighSchoolStudent,
    LegalDepartmentStaff, MasterEstablishmentManager, Operator, Speaker,
    StructureManager, Student, Visitor,
)


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
    ]

    list_filter = (
        ActivationFilter,
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
    ]

    list_filter = (
        ActivationFilter,
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
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
    ]

    list_filter = ()

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
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
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
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
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
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
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

        if request.user.is_establishment_manager():
            es = request.user.establishment
            Q_filter = Q(structures__establishment=es)|Q(establishment=es)

        return ImmersionUser.objects.filter(Q_filter,
                                            groups__name='REF-STR',
                                            **filter).order_by('last_name', 'first_name')

    def has_add_permission(self, request):
        return request.user.is_superuser


class LegalDepartmentStaffAdmin(HijackUserAdminMixin, CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'get_establishment',
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
