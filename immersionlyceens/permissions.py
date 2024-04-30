from .libs.utils import get_general_setting

from django.db.models import Q

def hijack_permissions(*, hijacker, hijacked):
    """Custom permissions to hijack users"""

    if not hijacked.is_active:
        return False

    if hijacker.is_superuser:
        return True

    # Check if custom hijack is active
    try:
        if get_general_setting('ACTIVATE_HIJACK'):
            # Operator could hijack all users except superuser & operator
            if hijacker.is_operator() and not hijacked.is_superuser and not hijacked.is_operator():
                return True

            # Master establishment manager could hijack all users except superuser, operator and master establishment manager
            if (
                hijacker.is_master_establishment_manager()
                and not hijacked.is_superuser
                and not hijacked.is_operator()
                and not hijacked.is_master_establishment_manager()
            ):
                return True

            # Establishment manager could hijack all users except superuser,
            # operator, master establishment manager, establishment manager
            # structure manager from his establishment, structure consultant from his establishment
            # Legal department staff from his establishment.
            if (
                hijacker.is_establishment_manager()
                and not hijacked.is_superuser
                and not hijacked.is_operator()
                and not hijacked.is_master_establishment_manager()
                and not hijacked.is_establishment_manager()
                and not hijacked.is_visitor()
                and not hijacked.is_student()
                and not hijacked.is_high_school_student()
                and hijacker.establishment == hijacked.establishment
            ):
                return True

            # Establishment manager could hijack students, visitors and high school students from anywhere
            elif (
                hijacker.is_establishment_manager() and
                hijacked.is_visitor() or hijacked.is_student() or hijacked.is_high_school_student()
            ):
                return True
    except (ValueError, NameError):
        pass

    return False
