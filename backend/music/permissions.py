from rest_framework import permissions
from django.utils import timezone # For checking release visibility

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

class CanViewTrack(permissions.BasePermission):
    """
    Permission to check if a track can be viewed.
    A track can be viewed if:
    - The request is for a safe method (GET, HEAD, OPTIONS) AND:
        - The track's release is published and its release_date is not in the future.
        - OR the requesting user is the owner of the track's release's artist.
        - OR the requesting user is a staff member.
    - For unsafe methods (PUT, PATCH, DELETE), it relies on IsOwnerOrReadOnly (or similar)
      being checked *in addition* by the viewset. This permission is primarily for read access.
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a Track instance
        if not hasattr(obj, 'release') or not obj.release:
            return False # Should not happen with valid data

        release = obj.release

        # Staff users can see everything
        if request.user and request.user.is_staff:
            return True
            
        # Check if the user is the owner of the artist of the release
        is_artist_owner = False
        if request.user and request.user.is_authenticated:
            if hasattr(release, 'artist') and release.artist and \
               hasattr(release.artist, 'user') and release.artist.user:
                is_artist_owner = (release.artist.user.id == request.user.id)
        
        if is_artist_owner:
            return True

        # For everyone else, check if the release is published and visible
        is_release_visible = release.is_published and release.release_date <= timezone.now()
        
        if request.method in permissions.SAFE_METHODS:
            return is_release_visible
        
        # For unsafe methods, this permission alone is not enough.
        # The viewset should also use IsOwnerOrReadOnly for edit/delete.
        # This permission primarily gates *read* access based on release visibility.
        # If we reach here for an unsafe method, it means the user is not staff and not owner,
        # so they shouldn't be able to modify. But IsOwnerOrReadOnly is more direct for that.
        # For simplicity, we can say if it's not a safe method and they aren't owner/staff, deny.
        return False # Should be caught by IsOwnerOrReadOnly first for unsafe methods

class CanEditTrack(permissions.BasePermission):
    """
    Permission to check if a track can be edited/deleted.
    A track can be edited/deleted if the requesting user is the owner of the track's release's artist.
    """
    def has_object_permission(self, request, view, obj):
        # obj here is a Track instance
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not hasattr(obj, 'release') or not obj.release or \
           not hasattr(obj.release, 'artist') or not obj.release.artist or \
           not hasattr(obj.release.artist, 'user') or not obj.release.artist.user:
            return False # Invalid data structure for track ownership

        return obj.release.artist.user.id == request.user.id