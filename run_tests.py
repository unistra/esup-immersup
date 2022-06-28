import os
import sys

import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'immersionlyceens.settings.unittest'
django.setup()

from django.test.runner import DiscoverRunner


"""
Run tests script
"""

test_runner = DiscoverRunner(pattern='test_*.py', verbosity=2,
                             interactive=True, failfast=False)

test_apps = ['immersionlyceens']
test_apps = test_apps if len(sys.argv) <= 1 else sys.argv[1:]
failures = test_runner.run_tests(test_apps)
sys.exit(failures)
