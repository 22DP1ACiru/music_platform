from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

# Serializer for the built-in User model (only exposing basic info)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# Serializer for the UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'profile_picture', 'location', 'website_url']