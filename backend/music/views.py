from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Genre, Artist, Release, Track, Comment, Highlight # Ensure 'models' is imported
from .serializers import (
    GenreSerializer, ArtistSerializer, ReleaseSerializer,
    TrackSerializer, CommentSerializer, HighlightSerializer
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser
from music.permissions import IsOwnerOrReadOnly, CanViewTrack, CanEditTrack
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.http import FileResponse, Http404
import os
import mimetypes 
from django.db import models as django_models # Explicit import for Q objects

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all().order_by('name')
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    
    def perform_create(self, serializer):
        if Artist.objects.filter(user=self.request.user).exists():
             raise ValidationError("You already have an associated artist profile.")
        serializer.save(user=self.request.user)

class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['artist', 'genres', 'release_type'] 

    def get_queryset(self):
        user = self.request.user
        base_queryset = Release.objects.select_related('artist').prefetch_related('tracks', 'genres')
        visible_releases = base_queryset.filter(is_published=True, release_date__lte=timezone.now())

        if user.is_authenticated:
            if user.is_staff: 
                return base_queryset.all().order_by('-release_date')
            try:
                user_artist = Artist.objects.get(user=user)
                queryset = (visible_releases | base_queryset.filter(artist=user_artist)).distinct()
            except Artist.DoesNotExist:
                queryset = visible_releases
        else:
            queryset = visible_releases
        return queryset.order_by('-release_date')

    def perform_create(self, serializer):
        try:
            artist = Artist.objects.get(user=self.request.user)
            serializer.save(artist=artist)
        except Artist.DoesNotExist:
            raise PermissionDenied("You must have an artist profile to create releases.")

class TrackViewSet(viewsets.ModelViewSet):
    # queryset = Track.objects.select_related('release__artist').prefetch_related('genres') # Moved to get_queryset
    serializer_class = TrackSerializer
    # permission_classes = [IsAuthenticatedOrReadOnly, CanViewTrack, CanEditTrack] # Handled by get_permissions
    filterset_fields = ['release', 'genres']

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
            # For create, user must be authenticated. Ownership of release for track is tricky here.
            # Usually, tracks are created nested under a release, or release_id is validated.
            # CanEditTrack would require an object, which doesn't exist yet.
            # Let's assume the serializer or perform_create will validate release ownership.
            permission_classes = [permissions.IsAuthenticated] 
        else: 
            permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanViewTrack, CanEditTrack]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        # Ensure related objects for permission checks are loaded efficiently
        qs = Track.objects.select_related(
            'release__artist', 
            'release__artist__user' # For artist owner check
        ).prefetch_related('genres')

        if self.action == 'list': # Apply filtering for list view
            if user.is_authenticated:
                if user.is_staff:
                    return qs 
                try:
                    user_artist = Artist.objects.get(user=user)
                    return qs.filter(
                        django_models.Q(release__is_published=True, release__release_date__lte=timezone.now()) |
                        django_models.Q(release__artist=user_artist)
                    ).distinct()
                except Artist.DoesNotExist:
                    return qs.filter(release__is_published=True, release__release_date__lte=timezone.now()).distinct()
            else:
                return qs.filter(release__is_published=True, release__release_date__lte=timezone.now()).distinct()
        return qs # For other actions, permissions handle object-level access


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HighlightViewSet(viewsets.ReadOnlyModelViewSet): 
    queryset = Highlight.objects.filter(is_active=True).select_related(
        'release__artist' 
    ).prefetch_related('release__genres').order_by('order', '-highlighted_at')
    serializer_class = HighlightSerializer
    permission_classes = [permissions.AllowAny]


def stream_track_audio(request, track_id):
    print(f"--- stream_track_audio for track_id: {track_id} ---") # DEBUG
    http_range = request.META.get('HTTP_RANGE')
    print(f"DEBUG: HTTP_RANGE header received: {http_range}") # DEBUG

    track = get_object_or_404(Track, pk=track_id)
    
    can_stream = False
    release = track.release
    if request.user and request.user.is_staff:
        can_stream = True
    elif request.user and request.user.is_authenticated:
        try:
            # Ensure artist profile is fetched correctly for comparison
            user_artist = Artist.objects.get(user=request.user) 
            if release.artist_id == user_artist.id: # Compare IDs
                can_stream = True
        except Artist.DoesNotExist:
            pass 
    
    if not can_stream: 
        if release.is_published and release.release_date <= timezone.now():
            can_stream = True
            
    if not can_stream:
        print(f"DEBUG: Permission denied for track {track_id}. User: {request.user}") # DEBUG
        raise Http404("Track not found or you do not have permission to stream it.")

    if not track.audio_file:
        print(f"DEBUG: No audio_file attribute for track {track_id}.") # DEBUG
        raise Http404("Audio file not found for this track.")
    if not track.audio_file.storage.exists(track.audio_file.name):
        print(f"DEBUG: Audio file '{track.audio_file.name}' does not exist in storage.") # DEBUG
        raise Http404("Audio file path does not exist in storage.")

    try:
        file_to_serve = track.audio_file.open('rb')
        print(f"DEBUG: Opened file '{track.audio_file.name}' for streaming.") # DEBUG
        
        content_type, encoding = mimetypes.guess_type(track.audio_file.name)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        if track.audio_file.name.lower().endswith('.wav') and content_type == 'audio/x-wav':
            content_type = 'audio/wav'
        print(f"DEBUG: Serving with Content-Type: {content_type}") # DEBUG

        response = FileResponse(file_to_serve, content_type=content_type, as_attachment=False)
        response['Accept-Ranges'] = 'bytes'
        
        # Log response details before returning, Django's FileResponse sets these internally
        # based on the presence of HTTP_RANGE.
        # We can't easily see the status code FileResponse *will* set here,
        # as it's determined later in the WSGI handling based on the range.
        print(f"DEBUG: FileResponse created. Accept-Ranges: {response.get('Accept-Ranges')}") # DEBUG
        
        return response
    except FileNotFoundError:
        print(f"DEBUG: FileNotFoundError for track {track_id} (should have been caught by storage.exists).") # DEBUG
        raise Http404("Audio file not found on the server's filesystem.")
    except Exception as e:
        print(f"ERROR serving audio file for track {track_id}: {e}") # DEBUG
        # Consider logging the full traceback for unexpected errors
        import traceback
        traceback.print_exc()
        raise Http404("An error occurred while trying to serve the audio file.")