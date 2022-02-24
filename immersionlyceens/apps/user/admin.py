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
from immersionlyceens.apps.core.admin import (
    ActivationFilter, AdminWithRequest, CustomUserAdmin, HighschoolListFilter,
)
from immersionlyceens.apps.core.models import (
    AccompanyingDocument, AnnualStatistics, BachelorMention, Building,
    Calendar, Campus, CancelType, CertificateLogo, CertificateSignature,
    Course, CourseType, Establishment, EstablishmentManager,
    EvaluationFormLink, EvaluationType, GeneralBachelorTeaching,
    GeneralSettings, HighSchool, HighSchoolLevel, HighSchoolManager,
    HighSchoolStudent, Holiday, Immersion, ImmersionUser, InformationText,
    LegalDepartmentStaff, MailTemplate, MasterEstablishmentManager,
    OffOfferEventType, Operator, PostBachelorLevel, PublicDocument, PublicType,
    Slot, Speaker, Structure, StructureManager, Student, StudentLevel,
    Training, TrainingDomain, TrainingSubdomain, UniversityYear, Vacation,
    Visitor,
)
from immersionlyceens.apps.immersion.models import HighSchoolStudentRecord


class HighschoolStudentAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='LYC').order_by('last_name', 'first_name')

class StudentAdmin(CustomUserAdmin):
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


class VisitorAdmin(CustomUserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'destruction_date',
        'get_edited_record',
        'get_validated_record',
    ]

    list_filter = (
        ('establishment', RelatedDropdownFilter),
        HighschoolListFilter,
    )

    def get_queryset(self, request):
        return ImmersionUser.objects.filter(groups__name='VIS').order_by('last_name', 'first_name')


class SpeakerAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='INTER').order_by('last_name', 'first_name')


class OperatorAdmin(CustomUserAdmin):
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


class EstablishmentManagerAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='REF-ETAB').order_by('last_name', 'first_name')


class MasterEstablishmentManagerAdmin(CustomUserAdmin):
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


class HighSchoolManagerAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='REF-LYC').order_by('last_name', 'first_name')


class StructureManagerAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='REF-STR').order_by('last_name', 'first_name')


class LegalDepartmentStaffAdmin(CustomUserAdmin):
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
        return ImmersionUser.objects.filter(groups__name='SRV-JUR').order_by('last_name', 'first_name')

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
