# pylint: disable=R0903,C0115,R0201
"""Serializer"""

from rest_framework import serializers, status
from django.contrib.auth.models import Group
from django.utils.translation import gettext, gettext_lazy as _
from django.db.models import Q
from django.conf import settings

from .models import (Campus, Establishment, Training, TrainingDomain, TrainingSubdomain,
    HighSchool, Course, Structure, Building, Visit, OffOfferEvent, ImmersionUser,
    HighSchoolLevel, Slot
)


class ImmersionUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImmersionUser
        fields = ('last_name', 'first_name', 'email')


class SpeakerSerializer(ImmersionUserSerializer):
    def validate(self, attrs):
        # Note : email (account) unicity is checked before serializer validation
        establishment = attrs.get('establishment', None)
        highschool = attrs.get('highschool', None)

        if not establishment and not highschool:
            raise serializers.ValidationError(_("Either an establishment or a high school is mandatory"))

        if establishment and establishment.data_source_plugin:
            raise serializers.ValidationError(
                _("Establishment '%s' has an account plugin, please create the speakers in the admin interface")
                % establishment.short_label
            )

        return super().validate(attrs)

    def create(self, validated_data):
        try:
            user = super().create(validated_data)
            Group.objects.get(name='INTER').user_set.add(user)
        except Exception as e:
            raise

        return user

    class Meta:
        model = ImmersionUser
        fields = ('last_name', 'first_name', 'email', 'establishment', 'id', 'highschool')


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


class CourseSerializer(serializers.ModelSerializer):
    """
    Course serializer
    """

    def validate(self, data):
        """
        check speakers/published status and that only structures OR highschool are set at the same time
        """
        published = data.get('published', False) in ('true', 'True', True)
        speakers = data.get('speakers')
        structure = data.get("structure")
        highschool = data.get("highschool")

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
        excludes = {'id': data.get('id')} if data.get('id') else {}

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
            return data


    class Meta:
        model = Course
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


class HighSchoolViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchool
        fields = ("id", "city", "label")


class HighSchoolSerializer(serializers.ModelSerializer):
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

        return super().validate(attrs)

    class Meta:
        model = HighSchool
        fields = "__all__"


class TrainingSerializer(serializers.ModelSerializer):
    """
    Training serializer
    """
    def validate(self, data):
        """
        check that only structures OR highschool are set at the same time
        """
        content = None
        structures = data.get("structures")
        highschool = data.get("highschool")
        label = data.get("label")

        if not structures and not highschool:
            content = gettext("'%s' : please provide a structure or a high school") % label
        elif structures and highschool:
            content = gettext("'%s' : high school and structures can't be set together. Please choose one.") % label

        excludes = {}
        if data.get("id"):
            excludes['id'] = data.get("id")

        structure_establishments = [structure.establishment.id for structure in data.get("structures", [])]

        tr_queryset = Training.objects.exclude(**excludes).filter(
            Q(label__iexact=label,
              structures__establishment__in=structure_establishments)|
            Q(label__iexact=label,
              highschool=highschool)
        )

        if tr_queryset.exists():
            content = gettext(
                "A training with the label '%s' already exists within the same establishment or highschool"
            ) % label

        if content:
            raise serializers.ValidationError(detail=content, code=status.HTTP_400_BAD_REQUEST)

        return data

    class Meta:
        model = Training
        fields = "__all__"


class TrainingDomainSerializer(serializers.ModelSerializer):
    """Training domain serializer"""
    class Meta:
        model = TrainingDomain
        fields = "__all__"


class TrainingSubdomainSerializer(serializers.ModelSerializer):
    """Training sub domain serializer"""
    # training_domain = TrainingDomainSerializer(many=False, required=True)
    training_domain = serializers.PrimaryKeyRelatedField(
        queryset=TrainingDomain.objects.all(),
        many=False,
        required=True
    )

    class Meta:
        model = TrainingSubdomain
        fields = "__all__"


class TrainingHighSchoolSerializer(serializers.ModelSerializer):
    """Training serializer"""
    training_subdomains = serializers.SerializerMethodField("get_training_subdomains")
    can_delete = serializers.BooleanField()

    def get_training_subdomains(self, training):
        """get only active training subdomains"""
        query = training.training_subdomains.filter(active=True)
        serializer = TrainingSubdomainSerializer(instance=query, many=True)
        return serializer.data

    class Meta:
        model = Training
        fields = ("id", "label", "training_subdomains", "active", "can_delete")


class VisitSerializer(serializers.ModelSerializer):
    establishment = EstablishmentSerializer(many=False, read_only=True)
    structure = StructureSerializer(many=False, read_only=True)
    highschool = HighSchoolViewSerializer(many=False, read_only=True)
    speakers = ImmersionUserSerializer(many=True, read_only=True)
    can_delete = serializers.BooleanField()

    published_slots_count = serializers.IntegerField()
    slots_count = serializers.IntegerField()
    registrations_count = serializers.IntegerField()
    n_places = serializers.IntegerField(source="free_seats")

    class Meta:
        model = Visit
        fields = "__all__"


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

    class Meta:
        model = OffOfferEvent
        fields = "__all__"


class HighSchoolLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchoolLevel
        fields = "__all__"


class SlotSerializer(serializers.ModelSerializer):
    """
    Slot serializer
    """

    def validate(self, data):
        """
        For now, only create course slots
        """
        course = data.get("course")
        course_type = data.get("course_type")
        campus = data.get("campus")
        building = data.get("building")
        visit = data.get("visit")
        event = data.get("event")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        face_to_face = data.get("face_to_face", True)
        published = data.get("published", False)
        speakers = data.get("speakers")
        allowed_establishments = data.get("allowed_establishments")
        allowed_highschools = data.get("allowed_highschools")
        allowed_highschool_levels = data.get("allowed_highschool_levels")
        allowed_student_levels  = data.get("allowed_student_levels")
        allowed_post_bachelor_levels = data.get("allowed_post_bachelor_levels")

        details = {}

        # Slot type
        if not any([course, visit, event]):
            raise serializers.ValidationError(
                detail=_("A slot requires at least a 'course', a 'visit' or an 'event' object"),
                code=status.HTTP_400_BAD_REQUEST
            )

        if published:
            required_fields = ["n_places", "date", "start_time", "end_time", "speakers"]

            if face_to_face:
                required_fields.append("room")
            elif event or visit:
                required_fields.append("url")

            for rfield in required_fields:
                if not data.get(rfield):
                    details[rfield] = _("Field '%s' is required for a new published slot") % rfield

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
                        _("Speaker '%s' is not linked to course '%s'") % (speaker, course)
                    )

        if details:
            raise serializers.ValidationError(
                detail=details,
                code=status.HTTP_400_BAD_REQUEST
            )

        # Restrictions
        # Common to courses, visits and events
        data["levels_restrictions"] = any([allowed_highschool_levels, allowed_student_levels, allowed_post_bachelor_levels])

        if course or event:
            data["establishments_restrictions"] = any([allowed_establishments, allowed_highschools])
        elif visit:
            # No establishment restriction
            data["establishments_restrictions"] = False
            data["allowed_establishments"] = None
            data["allowed_highschools"] = None

        return data

    class Meta:
        model = Slot
        fields = "__all__"