class DisplayException(Exception):
    """
    Regular exception but with an extra "display" kwarg
    Display exception value on 500 page if 'display' is True
    """
    def __init__(self, *args, **kwargs):
        self.display = kwargs.pop("display", False)
        super().__init__(*args)