from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Checks for obj.user, obj.owner, or obj.artist.user.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        # Ensure request.user is authenticated for write methods
        if not request.user or not request.user.is_authenticated:
            return False

        # Check for common ownership patterns
        # For Release
        if hasattr(obj, 'artist') and hasattr(obj.artist, 'user'): 
            return obj.artist.user.id == request.user.id # Compare IDs

        # For Track
        # Check if obj is a Track, then check its release's artist's user
        # Need to be careful with the order of these checks if models share attribute names
        from .models import Track # Local import to avoid circular dependency if permissions is imported elsewhere early
        if isinstance(obj, Track):
            if hasattr(obj, 'release') and obj.release and \
               hasattr(obj.release, 'artist') and obj.release.artist and \
               hasattr(obj.release.artist, 'user') and obj.release.artist.user:
                return obj.release.artist.user.id == request.user.id # Compare IDs
            return False # Track doesn't have the expected ownership chain

        # For Artist, Comment, UserProfile (assuming UserProfile has a 'user' field)
        if hasattr(obj, 'user'): 
            return obj.user.id == request.user.id # Compare IDs
        
        # For Playlist (assuming Playlist has an 'owner' field which is a User)
        if hasattr(obj, 'owner'): 
            return obj.owner.id == request.user.id # Compare IDs


        # Deny if no ownership attribute found or specific check failed
        return False