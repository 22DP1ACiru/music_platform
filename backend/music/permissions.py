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

        # Check for common ownership patterns
        if hasattr(obj, 'user'): # For Artist, Comment, UserProfile
            return obj.user == request.user
        if hasattr(obj, 'owner'): # For Playlist
            return obj.owner == request.user
        if hasattr(obj, 'artist') and hasattr(obj.artist, 'user'): # For Release, Track
            # For Track, we check the release's artist
            if hasattr(obj, 'release') and hasattr(obj.release, 'artist'):
                 return obj.release.artist.user == request.user
            # For Release directly
            return obj.artist.user == request.user

        # Deny if no ownership attribute found
        return False