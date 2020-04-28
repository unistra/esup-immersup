#!/usr/bin/env python
"""
Import higher education institutions from an opendata platform
"""
import logging
import requests
import sys

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from immersionlyceens.apps.core.models import HigherEducationInstitution

logger = logging.getLogger(__name__)

# Source => model fields mapping
fields_mapping = {
    'uai': 'uai_code',
    'uo_lib':'label',
    'dep_nom':'department',
    'com_nom':'city',
    'code_postal_uai':'zip_code',
    'pays_etranger_acheminement':'country'
}


class Command(BaseCommand):
    """
    Base import command
    """
    def handle(self, *args, **options):
        # pagination settings
        rows = 50
        start = 0
        url = settings.INSTITUTES_URL % (rows, start)

        try:
            r = requests.get(url)
            json_data = r.json()
        except Exception as e:
            logger.exception("Cannot get institutes from url %s", url)
            return False

        current_institutes = {}
        current_institutes_objs = {}

        for inst in HigherEducationInstitution.objects.all():
            current_institutes[inst.uai_code] = { k:getattr(inst, k) for k in fields_mapping.values() }
            current_institutes_objs[inst.uai_code] = inst

        created = 0
        updated = 0
        not_updated = 0
        deleted = 0
        key_list = []

        while json_data['records']:
            for json_inst in json_data['records']:
                json_uai = json_inst['fields'].get('uai', None)

                if not json_uai:
                    logger.error("Json error (code_uai) : %s", json_inst)
                    continue

                key_list.append(json_uai)

                new_data = {fields_mapping[k]: str(json_inst['fields'].get(k, '')) for k in fields_mapping.keys()}

                institute = current_institutes.get(json_uai, None)

                # New
                if not institute:
                    try:
                        new_institute = HigherEducationInstitution.objects.create(**new_data)
                        current_institutes[json_uai] = new_data.copy()
                        current_institutes_objs[json_uai] = new_institute
                        created += 1
                    except Exception as e:
                        logger.exception("Cannot create new institute from data : %s", new_data)
                else: # update
                    if new_data != institute:
                        inst = current_institutes_objs[json_uai]
                        for k, v in new_data.items():
                            setattr(inst, k, v)
                        inst.save()

                        updated += 1
                    else:
                        not_updated += 1

            try:
                start += rows
                url = settings.INSTITUTES_URL % (rows, start)
                r = requests.get(url)
                json_data = r.json()
            except Exception as e:
                logger.exception("Cannot get institutes from url %s", url)
                return False

        # Deletion
        current_keys = current_institutes.keys()
        delete_keys = set(key_list) - set(current_keys)

        for uai_code in delete_keys:
            try:
                HigherEducationInstitution.objects.get(pk=uai_code).delete()
                deleted += 1
            except HigherEducationInstitution.DoesNotExist:
                logger.error("Cannot purge HigherEducationInstitution object with code %s", uai_code)


        logger.info("%s institutes created", created)
        logger.info("%s institutes updated", updated)
        logger.info("%s institutes not updated", not_updated)
        logger.info("%s institutes deleted", deleted)

        # remaining elements in current_institutes should be deleted from database
        if len(delete_keys) - deleted:
            logger.info("%s institutes not deleted where they should have been", len(delete_keys) - deleted)
