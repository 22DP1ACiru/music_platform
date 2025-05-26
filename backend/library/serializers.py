from rest_framework import serializers
from .models import UserLibraryItem
from music.serializers import ReleaseSerializer # To nest release details

class UserLibraryItemSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    # Nest the full release details for easy display in the library
    release = ReleaseSerializer(read_only=True) 
    # For creation, we'll only need the release_id
    release_id = serializers.IntegerField(write_only=True, required=False) # Not required for list/retrieve

    class Meta:
        model = UserLibraryItem
        fields = [
            'id', 
            'user', 
            'release', 
            'release_id', # For write operations
            'acquired_at', 
            'acquisition_type',
            # 'order_item' # if you add this field
        ]
        read_only_fields = ('user', 'release', 'acquired_at') # User is set from request, release from release_id

    def create(self, validated_data):
        # User will be set in the view based on request.user
        # 'release_id' is popped and used to get the Release instance
        # 'acquisition_type' can be passed or defaulted in the view
        return UserLibraryItem.objects.create(**validated_data)

class AddToLibrarySerializer(serializers.Serializer):
    release_id = serializers.IntegerField(required=True)
    # Optional: allow specifying acquisition_type if not always 'FREE' initially
    acquisition_type = serializers.ChoiceField(
        choices=UserLibraryItem.ACQUISITION_CHOICES, 
        default='FREE', 
        required=False
    )
    def validate_release_id(self, value):
        from music.models import Release # Local import
        if not Release.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Release with this ID does not exist.")
        return value