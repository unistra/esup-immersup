from datetime import datetime, timedelta
from typing import Any, Dict
from unittest import TestCase

from django.template import TemplateSyntaxError
from immersionlyceens.apps.core import models as core_models
from immersionlyceens.libs.utils import (
    check_active_year, get_general_setting, get_information_text, render_text,
)


class UtilsTestCase(TestCase):
    def test_render_text__empty(self):
        content: str = ""
        data: Dict[str, Any] = {}
        result: str = ""

        self.assertEqual(render_text(content, data), result)

    def test_render_text__basic_str(self):
        content: str = "hello world"
        data: Dict[str, Any] = {}
        result: str = content

        self.assertEqual(render_text(content, data), result)

    def test_render_text__basic_data(self):
        content: str = "hello {{ hello }}"
        data: Dict[str, Any] = {"hello": "world"}
        result: str = "hello world"

        self.assertEqual(render_text(content, data), result)

    def test_render_text__no_data(self):
        content: str = "hello {{ hello }}"
        data: Dict[str, Any] = {}
        result: str = "hello "

        self.assertEqual(render_text(content, data), result)

    def test_render_text__basic_condition(self):
        content: str = "{% if lang == 'fr' %}Bonjour tout le monde{% else %}Hello world{% endif %}"

        self.assertEqual(render_text(content, {"lang": "fr"}), "Bonjour tout le monde")
        self.assertEqual(render_text(content, {"lang": "en"}), "Hello world")

    def test_render_text__bad_templating(self):
        content: str = "{% if lang == 'fr' %}Bonjour tout le monde{% else %}Hello world"

        with self.assertRaises(TemplateSyntaxError):
            render_text(content, {"lang": "fr"})


    def test_check_active_year(self):
        today = datetime.today().date()
        u = core_models.UniversityYear.objects.create(
            label='Year',
            start_date=datetime.today().date() + timedelta(days=2),
            end_date=datetime.today().date() + timedelta(days=4),
            registration_start_date=today,
        )
        active_year = core_models.UniversityYear.objects.get(active=True)
        registration_is_available = active_year.registration_start_date <= today <= active_year.end_date
        today_in_range = active_year.start_date <= today <= active_year.end_date
        self.assertEqual(check_active_year(), (registration_is_available, today_in_range, active_year))
        active_year.active=False
        active_year.save()
        u.delete()


    def test_get_general_setting(self):
        #g = GeneralSettings.objects.create()
        with self.assertRaises(NameError):
            get_general_setting('NOT_FOUND_SETTING')

        # Call function without parameters returns None
        self.assertEqual(get_general_setting(), None)

        # Call function for value of a sets setting
        g = core_models.GeneralSettings.objects.create(setting='EMPTY_PARAM', parameters={})
        with self.assertRaises(ValueError):
            get_general_setting('EMPTY_PARAM')

        g.delete()

        # Existing param
        g = core_models.GeneralSettings.objects.create(setting='NEW_PARAM', \
            parameters={'value':'PARAM', 'type':'TEXT', 'description':'PARAM'})

        self.assertEqual(get_general_setting('NEW_PARAM'),'PARAM')

        g.delete()

    def test_get_information_text(self):
        with self.assertRaises(NameError):
            get_information_text('NOT_FOUND_TEXT')

        # Call function without parameters returns None
        self.assertEqual(get_information_text(), None)

        # Call function for value of a sets text but without content
        i = core_models.InformationText.objects.create(label='EMPTY_TEXT', code='T1', content='')
        with self.assertRaises(ValueError):
            get_information_text('T1')

        i.delete()

        # Existing text
        i = core_models.InformationText.objects.create(label='TEXT', code='T2', content='TEXT')

        self.assertEqual(get_information_text('T2'),'TEXT')

        i.delete()
