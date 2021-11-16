from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Import ImmerSup initial datas"

    def handle(self, *args, **options) -> None:
        pass
