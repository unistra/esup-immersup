class Schedulable:
    """
    Class for commands we want to configure in 'Scheduled tasks'
    """
    _schedulable = True

    def is_schedulable(self):
        return self._schedulable