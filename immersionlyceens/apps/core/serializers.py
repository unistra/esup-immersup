from rest_framework import serializers

from .models import Campus, Establishment

class CampusSerializer(serializers.ModelSerializer):

    class Meta:
        model = Campus
        fields = "__all__"


class EstablishmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Establishment
        fields = "__all__"
