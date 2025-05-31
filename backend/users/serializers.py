from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile
from music.models import Artist # Import Artist model for ArtistSummarySerializer
from django.conf import settings

# A light-weight serializer for embedding basic artist info.
# This helps avoid potential circular dependencies if the full ArtistSerializer
# from music.serializers were to import UserSerializer from this file.
class ArtistSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Artist
        fields = ['id', 'name'] # Include basic fields needed for display

# Serializer for the UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    # user field is not included here as this serializer will be nested under UserSerializer
    artist_profile_data = ArtistSummarySerializer(source='user.artist_profile', read_only=True, allow_null=True)
    # Use source='user.artist_profile' to correctly access the artist profile
    # related from User -> ArtistProfile. Requires Artist model to have one-to-one with User.
    # The Artist model's user field has related_name='artist_profile'.

    class Meta:
        model = UserProfile
        fields = ['id', 'bio', 'profile_picture', 'location', 'website_url', 'artist_profile_data']

# Serializer for the built-in User model (exposing basic info + profile)
class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True) # Nest the profile
    is_staff = serializers.BooleanField(read_only=True) # Added is_staff

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile', 'is_staff'] # Add 'is_staff'


# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2')

    def validate_username(self, value):
        username_lower = value.lower()
        forbidden_list = getattr(settings, 'FORBIDDEN_USERNAME_SUBSTRINGS', [])
        for forbidden_word in forbidden_list:
            if forbidden_word.lower() in username_lower:
                raise serializers.ValidationError(
                    f"Username cannot contain the word '{forbidden_word}'."
                )
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        if User.objects.filter(email=attrs['email']).exists():
             raise serializers.ValidationError({"email": "Email already taken."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        UserProfile.objects.create(user=user) # Ensure UserProfile is created
        return user