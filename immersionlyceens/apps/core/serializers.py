# pylint: disable=R0903,C0115,R0201
"""Serializer"""

from rest_framework import serializers

from .models import (Campus, Establishment, Training, TrainingSubdomain, HighSchool,
    Course, Structure, Building, Visit, OffOfferEvent, ImmersionUser, HighSchoolLevel,
    PostBachelorLevel, StudentLevel
)
from ..immersion.models import VisitorRecord


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
    """Training sub domains serializer"""
    class Meta:
        model = TrainingSubdomain
        fields = ("id", "label", "active")


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
