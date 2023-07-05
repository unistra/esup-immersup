class Schedulable:
    """
    Class for commands we want to configure in 'Scheduled tasks'
    """
    schedulable = True

    def is_schedulable(self):
        return self.schedulable