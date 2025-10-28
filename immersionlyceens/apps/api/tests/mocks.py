"""
Mocks for unit tests
"""

def mocked_ldap_connection(*args, **kwargs):
    """
    Fake LDAP connection (do nothing)
    """
    pass

def mocked_ldap_bind(*args, **kwargs):
    """
    Fake LDAP bind (do nothing)
    """
    pass

def mocked_search_user(search_value):
    """
    Return a user
    """

    # The user exists :
    if search_value == "new_user@domain.tld":
        return [{
            'email': 'new_user@domain.tld',
            'firstname': 'Martine',
            'lastname': 'Dubois',
            'display_name': 'Martine Dubois (MAI)'
        }]
    else:
        return []