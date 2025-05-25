from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Genre, Artist, Release, Track, Comment, Highlight # Ensure 'models' is imported if Track uses it.
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
import mimetypes # Import mimetypes module

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
                owned_releases = base_queryset.filter(artist=user_artist)
                # Use models.Q from Django directly
                from django.db import models as django_models # Avoid conflict if you have local 'models'
                queryset = (visible_releases | owned_releases).distinct()
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
    queryset = Track.objects.select_related('release__artist').prefetch_related('genres')
    serializer_class = TrackSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, CanViewTrack, CanEditTrack] 
    filterset_fields = ['release', 'genres']

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated, CanEditTrack] 
        else: 
            permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanViewTrack, CanEditTrack]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        qs = Track.objects.select_related('release__artist', 'release__artist__user').prefetch_related('genres')


        if user.is_authenticated:
            if user.is_staff:
                return qs 
            try:
                user_artist = Artist.objects.get(user=user)
                # Use models.Q from Django directly
                from django.db import models as django_models
                return qs.filter(
                    django_models.Q(release__is_published=True, release__release_date__lte=timezone.now()) |
                    django_models.Q(release__artist=user_artist)
                ).distinct()
            except Artist.DoesNotExist:
                from django.db import models as django_models
                return qs.filter(django_models.Q(release__is_published=True, release__release_date__lte=timezone.now())).distinct()
        else:
            from django.db import models as django_models
            return qs.filter(django_models.Q(release__is_published=True, release__release_date__lte=timezone.now())).distinct()


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
    track = get_object_or_404(Track, pk=track_id)
    
    can_stream = False
    release = track.release
    if request.user and request.user.is_staff:
        can_stream = True
    elif request.user and request.user.is_authenticated:
        try:
            user_artist = Artist.objects.get(user=request.user)
            if release.artist == user_artist:
                can_stream = True
        except Artist.DoesNotExist:
            pass 
    
    if not can_stream: 
        if release.is_published and release.release_date <= timezone.now():
            can_stream = True
            
    if not can_stream:
        raise Http404("Track not found or you do not have permission to stream it.")

    if not track.audio_file:
        raise Http404("Audio file not found for this track.")
    if not track.audio_file.storage.exists(track.audio_file.name):
        raise Http404("Audio file path does not exist in storage.")

    try:
        # Guess MIME type, default to application/octet-stream if unknown
        content_type, encoding = mimetypes.guess_type(track.audio_file.name)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Specifically override for .wav if it's guessed as x-wav
        if track.audio_file.name.lower().endswith('.wav') and content_type == 'audio/x-wav':
            content_type = 'audio/wav'

        response = FileResponse(track.audio_file.open('rb'), content_type=content_type, as_attachment=False)
        response['Accept-Ranges'] = 'bytes'
        return response
    except FileNotFoundError:
        raise Http404("Audio file not found on the server's filesystem.")
    except Exception as e:
        print(f"Error serving audio file for track {track_id}: {e}")
        raise Http404("An error occurred while trying to serve the audio file.")