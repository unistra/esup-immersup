# pylint: disable=R0903,C0115,R0201
"""Serializer"""
from collections import OrderedDict
from django_countries.serializers import CountryFieldMixin
from rest_framework import serializers, status
from rest_framework.validators import UniqueTogetherValidator

from typing import Any, Dict, List, Optional, Tuple, Union

from django.contrib.auth.models import Group
from django.utils.translation import gettext, gettext_lazy as _
from django.db.models import Q
from django.conf import settings

from immersionlyceens.libs.api.accounts import AccountAPI
from immersionlyceens.libs.utils import get_general_setting

from .models import (Campus, Establishment, Training, TrainingDomain, TrainingSubdomain,
    HighSchool, Course, Structure, Building, OffOfferEvent, ImmersionUser,
    HighSchoolLevel, UserCourseAlert, Slot, CourseType, Period, UAI
)

class AsymetricRelatedField(serializers.PrimaryKeyRelatedField):
    """
    Allow a serialized relation field to be used this way :
    - POST : use the id of the object in POST data
    - GET : returns the serialized related object
    """
    def to_representation(self, value):
        return self.serializer_class(value).data

    def get_queryset(self):
        if self.queryset:
            return self.queryset
        return self.serializer_class.Meta.model.objects.all()

    def get_choices(self, cutoff=None):
        queryset = self.get_queryset()
        if queryset is None:
            return {}

        if cutoff is not None:
            queryset = queryset[:cutoff]

        return OrderedDict([(
            item.pk,
            self.display_value(item)
        ) for item in queryset
        ])

    def use_pk_only_optimization(self):
        return False

    @classmethod
    def from_serializer(cls, serializer, name=None, args=(), kwargs={}):
        if name is None:
            name = f"{serializer.__name__}AsymetricAutoField"

        return type(name, (cls,), {"serializer_class": serializer})


class ImmersionUserSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        if not validated_data.get('username'):
            validated_data['username'] = validated_data.get('email')

        return super().create(validated_data)

    class Meta:
        model = ImmersionUser
        fields = ('last_name', 'first_name', 'email', 'username')


class SpeakerSerializer(ImmersionUserSerializer):
    def validate(self, attrs):
        # Note : email (account) unicity is checked before serializer validation
        filter = {}
        establishment = attrs.get('establishment', None)
        highschool = attrs.get('highschool', None)
        email = attrs.get("email")

        try:
            ImmersionUser.objects.get(email__iexact=email.strip())
            raise serializers.ValidationError(_("A user with this email address already exists"))
        except ImmersionUser.DoesNotExist:
            pass

        # check fields depending on establishment / highschool
        if establishment or highschool:
            if establishment.data_source_plugin:
                if not email:
                    raise serializers.ValidationError(
                        _("Establishment '%s' has an account plugin, the email is mandatory")
                        % establishment.short_label
                    )

                # ================ duplicated code - rewrite this elsewhere ====================== #
                account_api: AccountAPI = AccountAPI(establishment)
                ldap_response: Union[bool, List[Any]] = account_api.search_user(
                    search_value=email.strip(),
                    search_attr=account_api.EMAIL_ATTR
                )
                if not ldap_response:
                    # not found
                    raise serializers.ValidationError(
                        detail=_("Speaker email '%(mail)s' not found in establishment '%(code)s'") % {
                            'email': email,
                            'code': establishment.code
                        },
                        code=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    speaker = ldap_response[0]
                    new_attrs = {
                        "username": speaker['email'],
                        "last_name": speaker['lastname'],
                        "first_name": speaker['firstname'],
                        "email": speaker['email'],
                    }

                    attrs.update(new_attrs)
                # =============================================================================== #
            else:
                mandatory_fields = ['last_name', 'first_name', 'email']
                for field in mandatory_fields:
                    if field not in attrs or attrs.get(field) is None:
                        raise serializers.ValidationError(
                            _("These field are mandatory : %s") % ", ".join(mandatory_fields)
                        )
        else:
            raise serializers.ValidationError(_("Either an establishment or a high school is mandatory"))

        return super().validate(attrs)


    def create(self, validated_data):
        try:
            user = super().create(validated_data)
            Group.objects.get(name='INTER').user_set.add(user)
        except Exception as e:
            raise

        return user

    def to_representation(self, instance):
        """
        CREATE : Inject status and warning messages in response
        GET : add extra fields useful in datatables
        """
        data = super().to_representation(instance)

        if hasattr(self, "initial_data"):
            if isinstance(self.initial_data, list):
                objects = { c["email"]: c for c in self.initial_data }
                status = objects.get(data["email"]).get("status", "success")
                message = objects.get(data["email"]).get("msg", "")
            else:
                status = self.initial_data.get("status", "success")
                message = self.initial_data.get("msg", "")

            response = {
                "data": data,
                "status": status,
                "msg": message,
            }

            return response
        else:
            if instance:
                data['has_courses'] = instance.courses.exists()
                data['can_delete'] = not data['has_courses']

            return data

    class Meta:
        model = ImmersionUser
        fields = ('id', 'last_name', 'first_name', 'email', 'establishment', 'highschool', 'is_active')


class CampusSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        # Advanced test
        excludes = {}
        label_filter = {'label__iexact': attrs.get('label')}

        if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
            label_filter = {'label__unaccent__iexact': attrs.get('label')}

        if attrs.get('id'):
            excludes = {'id': attrs.get('id')}

        if Campus.objects.filter(establishment=attrs.get('establishment'), **label_filter).exclude(**excludes).exists():
            raise serializers.ValidationError(
                _("A Campus object with the same establishment and label already exists")
            )

        return super().validate(attrs)

    class Meta:
        model = Campus
        fields = "__all__"
        validators = []


class EstablishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establishment
        fields = "__all__"


class StructureSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        # Advanced test
        excludes = {}
        label_filter = {'label__iexact': attrs.get('label')}

        if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
            label_filter = {'label__unaccent__iexact': attrs.get('label')}

        if attrs.get('id'):
            excludes = {'id': attrs.get('id')}

        if Structure.objects.filter(
                establishment=attrs.get('establishment'),
                **label_filter
            ).exclude(**excludes).exists():
            raise serializers.ValidationError(
                _("A Structure object with the same establishment and label already exists")
            )

        return super().validate(attrs)

    class Meta:
        model = Structure
        fields = "__all__"


class BuildingSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        # Advanced test
        excludes = {}
        label_filter = {'label__iexact': attrs.get('label')}

        if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
            label_filter = {'label__unaccent__iexact': attrs.get('label')}

        if attrs.get('id'):
            excludes = {'id': attrs.get('id')}

        if Building.objects.filter(
                campus=attrs.get('campus'),
                **label_filter
            ).exclude(**excludes).exists():
            raise serializers.ValidationError(
                _("A Building object with the same campus and label already exists")
            )

        return super().validate(attrs)

    class Meta:
        model = Building
        fields = "__all__"
        validators = []
        """
        validators = [
            UniqueTogetherValidator(
                queryset=Building.objects.all(),
                fields=['campus', 'label'],
                message=_("A Building object with the same campus and label already exists")
            )
        ]
        """


class HighSchoolViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchool
        fields = ("id", "city", "label")


class TrainingDomainSerializer(serializers.ModelSerializer):
    """Training domain serializer"""
    class Meta:
        model = TrainingDomain
        fields = "__all__"


class TrainingSubdomainSerializer(serializers.ModelSerializer):
    """Training sub domain serializer"""
    training_domain = AsymetricRelatedField.from_serializer(TrainingDomainSerializer)(required=True, many=False)

    class Meta:
        model = TrainingSubdomain
        fields = "__all__"

class UAISerializer(serializers.ModelSerializer):
    """High schools UAI serializer"""
    class Meta:
        model = UAI
        fields = "__all__"


class HighSchoolSerializer(CountryFieldMixin, serializers.ModelSerializer):
    uai_codes = AsymetricRelatedField.from_serializer(UAISerializer)(required=False, many=True)

    def validate(self, attrs):
        # Advanced test
        excludes = {}
        filters = {
            'label__iexact': attrs.get('label'),
            'city__iexact': attrs.get('city')
        }

        if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
            filters = {
                'label__unaccent__iexact': attrs.get('label'),
                'city__unaccent__iexact': attrs.get('city'),
            }

        if attrs.get('id'):
            excludes = {'id': attrs.get('id')}

        if HighSchool.objects.filter(**filters).exclude(**excludes).exists():
            raise serializers.ValidationError(
                _("A high school object with the same label and city already exists")
            )

        # Student federation and UAI
        if attrs.get('uses_student_federation', False) is True:
            if not attrs.get('uai_codes', []):
                raise serializers.ValidationError(
                    _("You have to add at least one UAI code when using student federation")
                )
            else:
                for uai in attrs.get('uai_codes'):
                    try:
                        UAI.objects.get(pk=uai.code)
                    except UAI.DoesNotExist:
                        raise serializers.ValidationError(
                            _("UAI code %s not found") % uai.code
                        )

        return super().validate(attrs)

    class Meta:
        model = HighSchool
        fields = "__all__"
        validators = []


class TrainingSerializer(serializers.ModelSerializer):
    """
    Training serializer
    """
    # GET: full related object in serializer (asymetric : 'id' in POST, object in GET)
    training_subdomains = AsymetricRelatedField.from_serializer(TrainingSubdomainSerializer)(required=True, many=True)

    # may not exist in nested representation (like course_list)
    nb_courses = serializers.IntegerField(read_only=True)

    def validate(self, data):
        """
        check that only structures OR highschool are set at the same time
        """
        details = {}
        structures = data.get("structures")
        highschool = data.get("highschool")
        label = data.get("label")

        if not structures and not highschool:
            raise serializers.ValidationError(
                detail=gettext("'%s' : please provide a structure or a high school") % label,
                code=status.HTTP_400_BAD_REQUEST
            )
        elif structures and highschool:
            raise serializers.ValidationError(
                detail=gettext("'%s' : high school and structures can't be set together. Please choose one.") % label,
                code=status.HTTP_400_BAD_REQUEST
            )

        if not data.get("training_subdomains"):
            details["training_subdomains"] = gettext("'%s' : please provide at least one training subdomain") % label

        excludes = {}
        if data.get("id"):
            excludes['id'] = data.get("id")

        structure_establishments = [structure.establishment.id for structure in data.get("structures", [])]

        tr_queryset = Training.objects.prefetch_related('structures__establishment', 'highschool')\
            .exclude(**excludes)\
            .filter(
                Q(label__iexact=label,
                  structures__establishment__in=structure_establishments)|
                Q(label__iexact=label,
                  highschool=highschool)
            )

        if tr_queryset.exists():
            details["label"] = gettext(
                "A training with the label '%s' already exists within the same establishment or highschool"
            ) % label

        if details:
            raise serializers.ValidationError(detail=details, code=status.HTTP_400_BAD_REQUEST)

        return data

    class Meta:
        model = Training
        fields = ("id", "label", "training_subdomains", "nb_courses", "active", "url", "structures",
                  "highschool", "allowed_immersions")
        validators = []


class OffOfferEventSerializer(serializers.ModelSerializer):
    establishment = EstablishmentSerializer(many=False, read_only=True)
    structure = StructureSerializer(many=False, read_only=True)
    highschool = HighSchoolViewSerializer(many=False, read_only=True)
    event_type = serializers.StringRelatedField(many=False)
    speakers = ImmersionUserSerializer(many=True, read_only=True)
    can_delete = serializers.BooleanField()
    published_slots_count = serializers.IntegerField()
    slots_count = serializers.IntegerField()
    registrations_count = serializers.IntegerField()
    n_places = serializers.IntegerField(source="free_seats")

    def to_representation(self, instance):
        """
        Inject status and warning messages in response
        """
        data = super().to_representation(instance)

        if hasattr(self, "initial_data"):
            if isinstance(self.initial_data, list):
                objects = { c["label"]: c for c in self.initial_data }
                status = objects.get(data["label"]).get("status", "success")
                message = objects.get(data["label"]).get("msg", "")
            else:
                status = self.initial_data.get("status", "success")
                message = self.initial_data.get("msg", "")

            response = {
                "data": data,
                "status": status,
                "msg": message,
            }

            return response
        else:
            request = self.context.get("request")
            user_events = self.context.get("user_events", False)
            speaker_filter = {}

            if request and instance:
                user = request.user
                allowed_structures = user.get_authorized_structures()
                has_rights = False

                if user_events:
                    speaker_filter["speakers"] = user.linked_users()

                # ------------
                # Rights
                # ------------

                # Default, will be overridden later
                has_no_rights = all([
                    user.is_structure_consultant() or user.is_speaker(),
                    not user.is_master_establishment_manager(),
                    not user.is_establishment_manager(),
                    not user.is_structure_manager(),
                    not user.is_operator(),
                ])

                if instance.structure:
                    has_rights = all([
                        not has_no_rights,
                        (Structure.objects.filter(pk=instance.structure.id) & allowed_structures).exists()
                    ])
                elif instance.highschool:
                    has_rights = any([
                        user.is_master_establishment_manager(),
                        user.is_operator(),
                        instance.highschool == user.highschool
                    ])
                else:
                    has_rights = any([
                        user.is_master_establishment_manager(),
                        user.is_operator(),
                        user.is_establishment_manager() and user.establishment == instance.establishment
                    ])

                data['has_rights'] = has_rights
                data['slots_count'] = instance.slots_count(**speaker_filter)
                data['n_places'] = instance.free_seats(**speaker_filter)
                data['published_slots_count'] = instance.published_slots_count(**speaker_filter)
                data['registered_students_count'] = instance.registrations_count(**speaker_filter)
                data['registered_groups_count'] = instance.groups_registrations_count(**speaker_filter)
                data['can_delete'] = not instance.slots.exists()

            return data

    class Meta:
        model = OffOfferEvent
        fields = "__all__"


class HighSchoolLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchoolLevel
        fields = "__all__"

class CourseTypeSerializer(serializers.ModelSerializer):
    """Course Type serializer"""
    class Meta:
        model = CourseType
        fields = "__all__"

class CourseSerializer(serializers.ModelSerializer):
    """
    Course serializer
    """
    training = AsymetricRelatedField.from_serializer(TrainingSerializer)(required=True, many=False)
    structure = AsymetricRelatedField.from_serializer(StructureSerializer)(required=False, many=False)
    highschool = AsymetricRelatedField.from_serializer(HighSchoolSerializer)(required=False, many=False)
    speakers = AsymetricRelatedField.from_serializer(SpeakerSerializer)(required=False, many=True)

    def validate(self, data):
        """
        check speakers/published status and that only structures OR highschool are set at the same time
        """
        published = data.get('published', False) in ('true', 'True', True)
        speakers = data.get('speakers')
        structure = data.get("structure")
        highschool = data.get("highschool")
        excludes = {}

        if published and not speakers:
            raise serializers.ValidationError(
                detail=gettext("A published course requires at least one speaker"),
                code=status.HTTP_400_BAD_REQUEST
            )

        if not structure and not highschool:
            raise serializers.ValidationError(
                detail=gettext("Please provide a structure or a high school"),
                code=status.HTTP_400_BAD_REQUEST
            )
        elif structure and highschool:
            raise serializers.ValidationError(
                detail=gettext("High school and structures can't be set together. Please choose one."),
                code=status.HTTP_400_BAD_REQUEST
            )

        # Unicity test
        if self.instance and self.instance.id:
            excludes = {'id': self.instance.id}

        label_filter = {
            'label__iexact': data.get('label'),
            'training': data.get("training"),
            'highschool': highschool,
            'structure': structure
        }

        if settings.POSTGRESQL_HAS_UNACCENT_EXTENSION:
            label_filter.pop('label__iexact')
            label_filter['label__unaccent__iexact'] = data.get('label')

        if Course.objects.filter(
                **label_filter
            ).exclude(**excludes).exists():
            raise serializers.ValidationError(
                detail=gettext("A Course object with the same structure/highschool, training and label already exists"),
                code=status.HTTP_400_BAD_REQUEST
            )

        return data

    def to_representation(self, instance):
        """
        Inject status and warning messages in response
        """
        data = super().to_representation(instance)

        if hasattr(self, "initial_data"):
            if isinstance(self.initial_data, list):
                objects = { c["label"]: c for c in self.initial_data }
                status = objects.get(data["label"]).get("status", "success")
                message = objects.get(data["label"]).get("msg", "")
            else:
                status = self.initial_data.get("status", "success")
                message = self.initial_data.get("msg", "")

            response = {
                "data": data,
                "status": status,
                "msg": message,
            }

            return response
        else:
            request = self.context.get("request")
            user_courses = self.context.get("user_courses", False)
            speaker_filter = {}

            if request and instance:
                user = request.user
                allowed_structures = user.get_authorized_structures()
                has_rights = False

                if user_courses:
                    speaker_filter["speakers"] = user.linked_users()

                # Default
                has_no_rights = all([
                    user.is_structure_consultant() or user.is_speaker(),
                    not user.is_master_establishment_manager(),
                    not user.is_establishment_manager(),
                    not user.is_structure_manager(),
                    not user.is_operator(),
                ])

                if instance.structure:
                    has_rights = all([
                        not has_no_rights,
                        (Structure.objects.filter(pk=instance.structure.id) & allowed_structures).exists()
                    ])
                elif instance.highschool:
                    has_rights = any([
                        user.is_master_establishment_manager(),
                        user.is_operator(),
                        instance.highschool == user.highschool
                    ])
                else:
                    has_rights = any([
                        user.is_master_establishment_manager(),
                        user.is_operator(),
                        user.is_establishment_manager() and user.establishment == instance.establishment
                    ])

                data['has_rights'] = has_rights
                data['slots_count'] = instance.slots_count(**speaker_filter)
                data['n_places'] = instance.free_seats(**speaker_filter)
                data['published_slots_count'] = instance.published_slots_count(**speaker_filter)
                data['registered_students_count'] = instance.registrations_count(**speaker_filter)
                data['registered_groups_count'] = instance.groups_registrations_count(**speaker_filter)
                data['can_delete'] = not instance.slots.exists()
                data['alerts_count'] = instance.get_alerts_count()

            return data

    class Meta:
        model = Course
        fields =  [
            "id", "label", "training", "structure", "highschool", "published", "speakers", "url", "managed_by"
        ]
        validators = []


class SlotSerializer(serializers.ModelSerializer):
    """
    Slot serializer
    """

    def validate(self, data):
        """
        For now, only create course slots
        """
        period = data.get("period")
        date = data.get("date")
        course = data.get("course")
        course_type = data.get("course_type")
        campus = data.get("campus")
        building = data.get("building")
        event = data.get("event")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        place = data.get("place", Slot.FACE_TO_FACE)
        published = data.get("published", False)
        speakers = data.get("speakers")
        n_places = data.get('n_places')
        n_group_places = data.get('n_group_places')
        allowed_establishments = data.get("allowed_establishments")
        allowed_highschools = data.get("allowed_highschools")
        allowed_highschool_levels = data.get("allowed_highschool_levels")
        allowed_student_levels  = data.get("allowed_student_levels")
        allowed_post_bachelor_levels = data.get("allowed_post_bachelor_levels")
        allowed_bachelor_types = data.get("allowed_bachelor_types")
        allowed_bachelor_mentions = data.get("allowed_bachelor_mentions")
        allowed_bachelor_teachings = data.get("allowed_bachelor_teachings")
        allow_individual_registrations = data.get('allow_individual_registrations')
        allow_group_registrations = data.get('allow_group_registrations')
        group_mode = data.get('group_mode')
        public_group = data.get('public_group')
        details = {}

        enabled_groups = get_general_setting("ACTIVATE_COHORT")

        # Slot type
        if not any([course, event]):
            raise serializers.ValidationError(
                detail=_("A slot requires at least a 'course' or an 'event' object"),
                code=status.HTTP_400_BAD_REQUEST
            )

        if published:
            #TODO put required fields list when published (or not) in model
            required_fields = ["date", "period", "start_time", "end_time", "speakers"]

            if enabled_groups:
                if not allow_individual_registrations and not allow_group_registrations:
                    details['allow_individual_registrations'] = _(
                        "At least one of 'allow_individual_registrations' or 'allow_group_registrations' must be set"
                    )

                if allow_individual_registrations or not allow_group_registrations:
                    required_fields.append("n_places")
                elif allow_group_registrations:
                    required_fields.append("n_group_places")
                    required_fields.append("group_mode")
                    required_fields.append("public_group")
            else:
                required_fields.append("n_places")
                data["allow_individual_registrations"] = True

            if place in [Slot.FACE_TO_FACE, Slot.OUTSIDE]:
                required_fields.append("room")
            elif event:
                required_fields.append("url")

            for rfield in required_fields:
                if not data.get(rfield):
                    details[rfield] = _("Field '%s' is required for a new published slot") % rfield

        if period and date and not period.immersion_start_date <= date <= period.immersion_end_date:
            details["date"] = _("Invalid date for selected period : please check periods settings")

        if start_time and end_time and end_time <= start_time:
            details["end_time"] = _("end_time can't be set before or equal to start_time")

        if course:
            if not course_type:
                details["course_type"] = _("The course_type field is required when creating a new course slot")

            if course.structure:
                if not campus:
                    details["campus"] = \
                        _("The campus field is required when creating a new slot for a structure course")

                if not building:
                    details["building"] = \
                        _("The building field is required when creating a new slot for a structure course")

            if course.highschool:
                if campus:
                    details["campus"] = \
                        _("The campus field is forbidden when creating a new slot for a high school course")

                if building:
                    details["building"] = \
                        _("The building field is forbidden when creating a new slot for a high school course")

            for speaker in speakers:
                if speaker not in course.speakers.all():
                    if not details.get('speakers'):
                        details["speakers"] = []

                    details["speakers"].append(
                        _("Speaker '%(speaker)s' is not linked to course '%(course)s'") % {
                            'speaker': speaker,
                            'course': course
                        }
                    )

        if details:
            raise serializers.ValidationError(
                detail=details,
                code=status.HTTP_400_BAD_REQUEST
            )

        # Restrictions
        # Common to courses and events
        data["levels_restrictions"] = any([
            allowed_highschool_levels, allowed_student_levels, allowed_post_bachelor_levels
        ])

        data["bachelors_restrictions"] = any([
            allowed_bachelor_types, allowed_bachelor_mentions, allowed_bachelor_teachings
        ])

        data["establishments_restrictions"] = any([allowed_establishments, allowed_highschools])

        return data

    class Meta:
        model = Slot
        fields = "__all__"


class UserCourseAlertSerializer(serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=True)

    class Meta:
        model = UserCourseAlert
        fields = "__all__"

class PeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Period
        fields = "__all__"