from .libs.utils import get_general_setting


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
            if (
                hijacker.is_establishment_manager()
                and not hijacked.is_superuser
                and not hijacked.is_operator()
                and not hijacked.is_master_establishment_manager()
                and not hijacked.is_establishment_manager()
                and hijacker.establishment == hijacked.establishment
            ):
                return True
    except (ValueError, NameError):
        pass

    return False
