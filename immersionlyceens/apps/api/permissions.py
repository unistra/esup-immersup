from rest_framework.permissions import BasePermission, DjangoModelPermissions
from django.utils.translation import activate, LANGUAGE_SESSION_KEY, ugettext_lazy as _

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

class HighSchoolReadOnlyPermissions(BasePermission):
    """
    Grant GET permission only when querying high schools with a valid agreement
    (see procedure.html)
    """
    def has_permission(self, request, view):
        agreed = request.GET.get("agreed", 'false').lower() == "true"
        return request.method == "GET" and (agreed or request.user.is_authenticated)
