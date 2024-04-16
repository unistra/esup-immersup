def hijack_permissions(*, hijacker, hijacked):
    """ Custom permissions to hijack users """

    if not hijacked.is_active:
        return False

    if hijacker.is_superuser:
        return True

    if hijacker.is_staff and not hijacked.is_superuser:
        # TODO: check if the hijacker with staff could hijack ?
        return True

    # Operator could hicjack all users except superuser
    if hijacker.is_operator() and not hijacked.is_superuser:
        return True

    # Master establishment manager could hijack all users except superuser and operator
    if hijacker.is_master_establishment_manager() and not hijacked.is_superuser and not hijacked.is_operator():
        return True

     # Establishment manager could hijack all users except superuser, operator and master establishment manager
    if (
        hijacker.is_establishment_manager()
        and not hijacked.is_superuser
        and not hijacked.is_operator()
        and not hijacked.is_master_establishment_manager()
    ):
        return True

    return False
