from rest_framework import serializers

from .models import Campus, Establishment, Structure

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
