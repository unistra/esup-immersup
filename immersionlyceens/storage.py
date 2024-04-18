from django.contrib.staticfiles.storage import ManifestStaticFilesStorage


class ManifestStaticFilesStorageNotStrict(ManifestStaticFilesStorage):
    manifest_strict = False


class ManifestStaticFilesStorageWithoutSourceMap(ManifestStaticFilesStorage):
    """Storage class for static files"""

    def __init__(self, *args, **kwargs):
        self.missing_files = []
        super().__init__(*args, **kwargs)

    def hashed_name(self, name, *args, **kwargs):
        """
        Ignore missing files, e.g. non-existent background image referenced from css,js
        Returns the original filename if the referenced file doesn't exist.
        """
        try:
            result = super().hashed_name(name, *args, **kwargs)
        except ValueError as e:
            message = e.args[0].split(" with ")[0]
            self.missing_files.append(message)
            print(f"\x1b[0;30;41m{message}\x1b[0m")
            result = name
        return result

    def post_process(self, *args, **kwargs):
        yield from super().post_process(*args, **kwargs)
        for message in sorted(set(self.missing_files)):
            print(f"\x1b[0;30;41m{message}\x1b[0m")
