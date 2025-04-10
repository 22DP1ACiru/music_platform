from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils import timezone # For filtering releases
from .models import Genre, Artist, Release, Track, Comment, Highlight
from .serializers import (
    GenreSerializer, ArtistSerializer, ReleaseSerializer,
    TrackSerializer, CommentSerializer, HighlightSerializer
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from music.permissions import IsOwnerOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend 

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all().order_by('name')
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def perform_create(self, serializer):
        """Link the new artist to the requesting user and prevent duplicates."""
        if Artist.objects.filter(user=self.request.user).exists():
             raise ValidationError("You already have an associated artist profile.")
        # Save the instance, automatically linking the user from the request context
        serializer.save(user=self.request.user)

class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['artist', 'genre', 'release_type'] 

    def get_queryset(self):
        """
        Override to show:
        - All visible releases to anyone.
        - Unpublished/future releases to the owner artist.
        - All releases to admins.
        """
        user = self.request.user
        base_queryset = Release.objects.select_related('artist', 'genre').prefetch_related('tracks')

        # Publicly visible releases
        visible_releases = base_queryset.filter(
            is_published=True,
            release_date__lte=timezone.now()
        )

        if user.is_authenticated:
            try:
                # Get the Artist profile associated with the requesting user
                user_artist = Artist.objects.get(user=user)

                # Releases owned by the user (published or not, future or past)
                owned_releases = base_queryset.filter(artist=user_artist)

                # Combine visible releases OR owned releases, removing duplicates
                # Using Q objects for OR condition
                queryset = (visible_releases | owned_releases).distinct()

            except Artist.DoesNotExist:
                # User is logged in but doesn't have an associated Artist profile
                # They only see the publicly visible releases
                queryset = visible_releases
        else:
            # Anonymous users only see publicly visible releases
            queryset = visible_releases

        if user.is_staff:
            return base_queryset.all()

        return queryset

    def perform_create(self, serializer):
        """
        Ensure the release is associated with the user's Artist profile.
        """
        try:
            artist = Artist.objects.get(user=self.request.user)
            serializer.save(artist=artist)
        except Artist.DoesNotExist:
            # Handle error: User needs an Artist profile to create a release
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You must have an artist profile to create releases.")

class TrackViewSet(viewsets.ModelViewSet):
    queryset = Track.objects.select_related('release__artist', 'genre') # Optimization
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    # Add filtering by release later (e.g., /api/releases/1/tracks/)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    # Override perform_create to automatically set the user
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # Consider adding filtering by track later

class HighlightViewSet(viewsets.ReadOnlyModelViewSet): # Read-only for regular users
    # Only show active highlights, ordered appropriately
    queryset = Highlight.objects.filter(is_active=True).select_related(
        'release__artist' # Optimization
    ).order_by('order', '-highlighted_at')
    serializer_class = HighlightSerializer
    # Anyone can view highlights
    permission_classes = [permissions.AllowAny]
    # Admins would need a separate ViewSet or different permissions
    # on ModelViewSet if they need to create/edit highlights via API.
