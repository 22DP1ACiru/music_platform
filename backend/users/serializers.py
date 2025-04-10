from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import UserProfile
from music.serializers import ArtistSerializer
from music.models import Artist
from django.conf import settings

# Serializer for the built-in User model (only exposing basic info)
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

# Serializer for the UserProfile model
class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    artist_profile_data = serializers.SerializerMethodField(read_only=True) 

    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'bio', 'profile_picture', 'location', 'website_url', 'artist_profile_data']

    def get_artist_profile_data(self, obj):
        """Check if user has an artist profile and serialize it."""
        try:
            # obj is the UserProfile instance. Access the user, then the related artist profile.
            artist = obj.user.artist_profile
            # Pass context which might contain the request if needed by nested serializer
            return ArtistSerializer(artist, context=self.context).data
        except Artist.DoesNotExist:
            return None # Return null if no artist profile exists
        # Handle potential AttributeError if obj.user is somehow None (shouldn't happen with OneToOneField)
        except AttributeError:
             return None

# Serializer for user registration
class RegisterSerializer(serializers.ModelSerializer):
    # Add password confirmation field
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password] # Use Django's validators
    )
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        # Fields required for registration input
        fields = ('username', 'email', 'password', 'password2')

    def validate_username(self, value):
        """
        Check if the username contains any forbidden substrings (case-insensitive).
        """
        username_lower = value.lower() # Convert submitted username to lowercase
        # Get the forbidden list from settings, default to empty list if not set
        forbidden_list = getattr(settings, 'FORBIDDEN_USERNAME_SUBSTRINGS', [])

        for forbidden_word in forbidden_list:
            if forbidden_word.lower() in username_lower:
                raise serializers.ValidationError(
                    f"Username cannot contain the word '{forbidden_word}'."
                )

        # Check if username already exists
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")

        return value # Return the validated username

    def validate(self, attrs):
        # Check if passwords match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        # Check if email already exists
        if User.objects.filter(email=attrs['email']).exists():
             raise serializers.ValidationError({"email": "Email already taken."})

        return attrs

    def create(self, validated_data):
        # Create the user instance
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email']
        )

        # Set the hashed password and save the user
        user.set_password(validated_data['password'])
        user.save()

        # Create UserProfile automatically
        UserProfile.objects.create(user=user)

        return user