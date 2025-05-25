from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Playlist
from music.models import Track # Import Track
from .serializers import PlaylistSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from music.permissions import IsOwnerOrReadOnly
from django.db.models import Q

class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    # Ensure users only see their own playlists + public ones,
    # and can only edit their own.
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Show user's own playlists OR public ones
            return Playlist.objects.filter(
                Q(owner=user) | Q(is_public=True)
            ).select_related('owner').prefetch_related('tracks__release__artist', 'tracks__genres').distinct() # Optimization & avoid duplicates
        else:
            # Anonymous users only see public playlists
            return Playlist.objects.filter(is_public=True).select_related('owner').prefetch_related('tracks__release__artist', 'tracks__genres')

    # Automatically set owner on creation
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def add_track(self, request, pk=None):
        playlist = self.get_object() # This also checks object permissions via IsOwnerOrReadOnly
        track_id = request.data.get('track_id')

        if not track_id:
            return Response({'error': 'track_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            track_id = int(track_id)
            track = Track.objects.get(pk=track_id)
        except (ValueError, Track.DoesNotExist):
            return Response({'error': 'Track not found.'}, status=status.HTTP_404_NOT_FOUND)

        if playlist.tracks.filter(pk=track.id).exists():
            return Response({'message': 'Track already in playlist.'}, status=status.HTTP_200_OK)

        playlist.tracks.add(track)
        # No need to call playlist.save() for M2M add unless you change other fields.
        return Response({'message': 'Track added to playlist.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly]) # Using post for body, could be delete with track_id in URL
    def remove_track(self, request, pk=None):
        playlist = self.get_object() # Checks object permissions
        track_id = request.data.get('track_id')

        if not track_id:
            return Response({'error': 'track_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            track_id = int(track_id)
            track = Track.objects.get(pk=track_id)
        except (ValueError, Track.DoesNotExist):
            # If track doesn't exist, it can't be in the playlist anyway.
            return Response({'message': 'Track not found or already removed.'}, status=status.HTTP_200_OK)

        if not playlist.tracks.filter(pk=track.id).exists():
            return Response({'message': 'Track not in this playlist.'}, status=status.HTTP_200_OK)
            
        playlist.tracks.remove(track)
        return Response({'message': 'Track removed from playlist.'}, status=status.HTTP_200_OK)