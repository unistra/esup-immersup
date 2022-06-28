from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    help = "Import ImmerSup initial datas"

    def add_arguments(self, parser):
        parser.add_argument(
            "-g",
            "--goal",
            type=str,
            dest="goal",
            action="append",
            help="defines goal to use for import",
            choices=["prod", "preprod", "test", "docker-demo", "docker-demo"],
            default="test",
        )

    def handle(self, *args, **options):

        try:
            self.stdout.write(
                self.style.SUCCESS(f"initial datas import for '{options['goal']}'")
            )

            # loads context fixture datas depending on goal
            if options['goal'] == 'test':
                #call_command('loaddata', 'test_fixture_file')
                pass
            if options['goal'] == 'prod':
                #call_command('loaddata', 'prod_fixture_file')
                pass
            if options['goal'] == 'preprod':
                #call_command('loaddata', 'preprod_fixture_file')
                pass
            if options['goal'] == 'docker-demo':
                #call_command('loaddata', 'docker_demo_fixture_file')
                pass
            if options['goal'] == 'docker-dev':
                #call_command('loaddata', 'docker_dev_fixture_file')
                pass


            self.stdout.write(self.style.SUCCESS("initial datas import - done"))

        except Exception as e:
            self.stdout.write(self.style.ERROR("Error : %s" % e))
