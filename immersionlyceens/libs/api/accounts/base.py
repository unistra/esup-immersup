class BaseAccountsAPI:
    """
    Accounts API : Methods to implement to search & import accounts
    """
    @staticmethod
    def search_user(*args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def get_plugin_attrs(*args, **kwargs):
        raise NotImplementedError

    @staticmethod
    def check_settings(*args, **kwargs):
        raise NotImplementedError