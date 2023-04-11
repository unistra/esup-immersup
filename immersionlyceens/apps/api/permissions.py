from django.utils.translation import (
    LANGUAGE_SESSION_KEY, activate, ugettext_lazy as _,
)
from rest_framework.permissions import BasePermission, DjangoModelPermissions


class CustomDjangoModelPermissions(DjangoModelPermissions):
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': [],
        'HEAD': [],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class IsRefLycPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_high_school_manager()
        except AttributeError:
            return False


class IsTecPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_operator()
        except AttributeError:
            return False


class IsEstablishmentManagerPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_establishment_manager()
        except AttributeError:
            return False


class IsMasterEstablishmentManagerPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_master_establishment_manager()
        except AttributeError:
            return False


class IsStructureManagerPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_structure_manager()
        except AttributeError:
            return False


class IsSpeakerPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_speaker()
        except AttributeError:
            return False


class IsStudentPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_student()
        except AttributeError:
            return False


class IsHighSchoolStudentPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_high_school_student()
        except AttributeError:
            return False


class IsVisitorPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_visitor()
        except AttributeError:
            return False


class HighSchoolReadOnlyPermissions(BasePermission):
    """
    Grant GET permission only when querying high schools with a valid agreement
    (see procedure.html)
    """
    # FIXME : UPDATE REQUIRED WITH US 356
    def has_permission(self, request, view):
        agreed = request.GET.get("agreed", 'false').lower() == "true"
        return request.method == "GET" and (agreed or request.user.is_authenticated)


class SpeakersReadOnlyPermissions(BasePermission):
    """
    GET permission only
    """
    def has_permission(self, request, view):
        users = [
            request.user.is_high_school_manager(),
            request.user.is_establishment_manager(),
            request.user.is_master_establishment_manager(),
            request.user.is_structure_manager(),
            request.user.is_operator(),
        ]

        return request.method == "GET" and any(users)


class IsStructureConsultantPermissions(BasePermission):
    message = _("You're not allowed to access this ressource")

    def has_permission(self, request, view):
        try:
            return request.user.is_structure_consultant()
        except AttributeError:
            return False