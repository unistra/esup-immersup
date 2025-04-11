from .utils import get_or_create_user
class ManyMixin:
    """
    Get 'single' or 'many' serializer depending on incoming data
    """
    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        if data is not None:
            many = isinstance(data, list)

            # eliminate duplicates
            if many:
                data = [dict(t) for t in [tuple(d.items()) for d in data]]

            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(instance=instance, many=many, partial=partial)

class SpeakersManyMixin:
    """
    Get 'single' or 'many' serializer depending on incoming data
    """

    def get_serializer(self, instance=None, data=None, many=False, partial=False):
        """
        Look for speaker emails and try to create/add them to serializer data
        """
        if data is not None:
            many = isinstance(data, list)

            if many:
                for single_data in data:
                    try:
                        single_data = get_or_create_user(self.request, single_data)
                    except Exception:
                        raise
            else:
                try:
                    data = get_or_create_user(self.request, data)
                except Exception:
                    raise

            return super().get_serializer(instance=instance, data=data, many=many, partial=partial)
        else:
            return super().get_serializer(
                instance=instance,
                many=many,
                partial=partial,
                context={'user_filter': self.user_filter, 'request': self.request},
            )