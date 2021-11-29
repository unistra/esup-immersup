from typing import Dict, Any
from unittest import TestCase

from django.template import TemplateSyntaxError

from immersionlyceens.libs.utils import render_text


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
