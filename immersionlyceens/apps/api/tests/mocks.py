"""
Mocks for unit tests
"""

def mocked_ldap_connection(*args, **kwargs):
    pass

def mocked_search_user(search_value, search_attr):
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