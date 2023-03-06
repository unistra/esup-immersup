# pylint: disable=R0903,C0115,R0201
"""Serializer"""
from collections import OrderedDict
from rest_framework import serializers, status
from django.utils.translation import gettext
from django.db.models import Q

from .models import (Campus, Establishment, Training, TrainingDomain, TrainingSubdomain,
    HighSchool, Course, Structure, Building, Visit, OffOfferEvent, ImmersionUser,
    HighSchoolLevel, PostBachelorLevel, StudentLevel
)
from ..immersion.models import VisitorRecord

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
    class Meta:
        model = ImmersionUser
        fields = ('last_name', 'first_name', 'email')

class CampusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campus
        fields = "__all__"


class EstablishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Establishment
        fields = "__all__"


class StructureSerializer(serializers.ModelSerializer):
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
        content = None
        published = data.get('published', False) in ('true', 'True', True)
        speakers = data.get('speakers')
        structure = data.get("structure")
        highschool = data.get("highschool")

        if published and not speakers:
            content = gettext("A published course requires at least one speaker")

        if not structure and not highschool:
            content = gettext("Please provide a structure or a high school")
        elif structure and highschool:
            content = gettext("High school and structures can't be set together. Please choose one.")

        if content:
            raise serializers.ValidationError(detail=content, code=status.HTTP_400_BAD_REQUEST)

        return data

    class Meta:
        model = Course
        fields = "__all__"


class BuildingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Building
        fields = "__all__"


class HighSchoolViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchool
        fields = ("id", "city", "label")

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

class TrainingSerializer(serializers.ModelSerializer):
    """
    Training serializer
    """
    # GET: full related object in serializer (asymetric : 'id' in POST, object in GET)
    training_subdomains = AsymetricRelatedField.from_serializer(TrainingSubdomainSerializer)(required=True, many=True)
    can_delete = serializers.BooleanField(read_only=True)

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

        tr_queryset = Training.objects.exclude(**excludes).filter(
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
        fields = ("id", "label", "training_subdomains", "active", "can_delete", "url", "structures", "highschool")
        # fields = "__all__"


class TrainingDomainSerializer(serializers.ModelSerializer):
    """Training domain serializer"""
    class Meta:
        model = TrainingDomain
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
