import logging

from typing import Any, Dict, List, Optional, Tuple, Union
from rest_framework import generics, serializers, status
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth.models import Group

from immersionlyceens.apps.core.models import Structure, ImmersionUser
from immersionlyceens.libs.api.accounts import AccountAPI

logger = logging.getLogger(__name__)

def get_or_create_user(request, data):
    """
    When creating or updating a course :
    - if a highschool is present, look for existing ImmersionUsers
    else
    - if a structure is present (not a highschool),
    - & if the structure establishment is linked to an account provider (eg. LDAP),
    - & if data has an 'emails' field (list)
    then search for existing ImmersionUser accounts matching these emails
    or
    look for these accounts in the establishment account provider in order to create new ImmersionUsers
    :param request: request object
    :param data: POST data
    :return: speakers id
    """
    highschool_id = data.get("highschool")
    structure_id = data.get("structure")
    emails = data.get("emails", [])
    establishment = None
    speaker_user = None
    send_creation_msg = False
    user_filter = {}

    # Validation exception will be thrown by the serializer
    if not highschool_id and not structure_id:
        return data

    if highschool_id:
        user_filter = {'highschool__id': highschool_id}
    elif structure_id:
        try:
            structure = Structure.objects.get(pk=structure_id)
            establishment = structure.establishment
            user_filter = {'establishment__id': establishment.id}
        except Structure.DoesNotExist:
            logger.info(f"get_or_create_user: structure {structure_id} not found")
            raise

    for email in emails:
        try:
            speaker_user = ImmersionUser.objects.get(email__iexact=email.strip(), **user_filter)
            data.get("speakers", []).append(speaker_user.id)
        except ImmersionUser.DoesNotExist:
            if not establishment or not establishment.provides_accounts():
                # High school or establishment without account provider : reject
                raise serializers.ValidationError(
                    detail=_(
                        "Course '%(label)s' : speaker '%(email)s' has to be manually created before using it in a course")
                           % {'label': data.get("label"), 'email': email},
                    code=status.HTTP_400_BAD_REQUEST
                )

            account_api: AccountAPI = AccountAPI(establishment)
            api_response: Union[bool, List[Any]] = account_api.search_user(
                search_value=email.strip(),
                search_attr=account_api.EMAIL_ATTR
            )

            # not found
            if not api_response:
                raise serializers.ValidationError(
                    detail=_("Course '%(label)s' : speaker email '%(email)s' not found in establishment '%(code)s'")
                           % {'label': data.get("label"), 'email': email, 'code': establishment.code},
                    code=status.HTTP_400_BAD_REQUEST
                )

            speaker = api_response[0]
            speaker_user = ImmersionUser.objects.create(
                username=speaker['email'],
                last_name=speaker['lastname'],
                first_name=speaker['firstname'],
                email=speaker['email'],
                establishment=establishment
            )
            send_creation_msg = True

        # Add INTER group to speaker
        try:
            Group.objects.get(name='INTER').user_set.add(speaker_user)
        except Exception as e:
            raise serializers.ValidationError(
                detail=_("Couldn't add group 'INTER' to user '%(username)s' : %(exception)s")
                       % {'username': speaker_user.username, 'exception': e},
                code=status.HTTP_400_BAD_REQUEST
            )

        if send_creation_msg:
            msg = speaker_user.send_message(request, 'CPT_CREATE')

            if msg:
                data.update({
                    "status": "warning",
                    "msg": {speaker_user.email: msg}
                })

        data.get("speakers", []).append(speaker_user.pk)

    return data