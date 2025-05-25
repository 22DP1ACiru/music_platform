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
from rest_framework.exceptions import ValidationError, PermissionDenied

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
        serializer.save(user=self.request.user)

class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    # Updated filterset_fields, 'genre' will now filter based on the ManyToMany 'genres' field
    filterset_fields = ['artist', 'genres', 'release_type'] 

    def get_queryset(self):
        """
        Override to show:
        - All visible releases to anyone.
        - Unpublished/future releases to the owner artist.
        - All releases to admins.
        """
        user = self.request.user
        # Updated to prefetch_related for 'genres' M2M field
        base_queryset = Release.objects.select_related('artist').prefetch_related('tracks', 'genres')

        visible_releases = base_queryset.filter(
            is_published=True,
            release_date__lte=timezone.now()
        )

        if user.is_authenticated:
            try:
                user_artist = Artist.objects.get(user=user)
                owned_releases = base_queryset.filter(artist=user_artist)
                from django.db.models import Q
                queryset = (visible_releases | owned_releases).distinct()
            except Artist.DoesNotExist:
                queryset = visible_releases
        else:
            queryset = visible_releases

        if user.is_staff:
            return base_queryset.all().order_by('-release_date')

        return queryset.order_by('-release_date')

    def perform_create(self, serializer):
        try:
            artist = Artist.objects.get(user=self.request.user)
            serializer.save(artist=artist) # genre_names is handled in serializer.create
        except Artist.DoesNotExist:
            raise PermissionDenied("You must have an artist profile to create releases.")

class TrackViewSet(viewsets.ModelViewSet):
    # Updated to prefetch_related for 'genres' M2M field
    queryset = Track.objects.select_related('release__artist').prefetch_related('genres')
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    # Add filtering by release later (e.g., /api/releases/1/tracks/)
    # If you want to filter tracks by genres directly on this ViewSet:
    filterset_fields = ['release', 'genres'] # Added genres for filtering

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HighlightViewSet(viewsets.ReadOnlyModelViewSet): 
    queryset = Highlight.objects.filter(is_active=True).select_related(
        'release__artist' 
    ).prefetch_related('release__genres').order_by('order', '-highlighted_at') # Also prefetch genres for highlighted releases
    serializer_class = HighlightSerializer
    permission_classes = [permissions.AllowAny]