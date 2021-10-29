from rest_framework import serializers

from .models import Campus, Establishment, Training, TrainingSubdomain, HighSchool


class CampusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campus
        fields = "__all__"


class EstablishmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Establishment
        fields = "__all__"


class HighSchoolViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HighSchool
        fields = ("id", "label")


class TrainingSubdomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingSubdomain
        fields = ("id", "label", "active")


class TrainingHighSchoolSerializer(serializers.ModelSerializer):
    training_subdomains = serializers.SerializerMethodField("get_training_subdomains")
    highschool = HighSchoolViewSerializer()

    def get_training_subdomains(self, training):
        query = training.training_subdomains.filter(active=True)
        serializer = HighSchoolViewSerializer(instance=query, many=True)
        return serializer.data

    class Meta:
        model = Training
        fields = ("id", "label", "training_subdomains", "highschool", "active")
