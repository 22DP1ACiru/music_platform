from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Playlist
from music.models import Track # Import Track
from .serializers import PlaylistSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from music.permissions import IsOwnerOrReadOnly
from django.db.models import Q, Count # Import Count

class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = Playlist.objects.annotate(track_count=Count('tracks')) # Annotate with track_count

        if user.is_authenticated:
            return queryset.filter(
                Q(owner=user) | Q(is_public=True)
            ).select_related('owner').prefetch_related('tracks__release__artist', 'tracks__genres').distinct()
        else:
            return queryset.filter(is_public=True).select_related('owner').prefetch_related('tracks__release__artist', 'tracks__genres')

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def add_track(self, request, pk=None):
        playlist = self.get_object()
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
        return Response({'message': 'Track added to playlist.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOrReadOnly])
    def remove_track(self, request, pk=None):
        playlist = self.get_object()
        track_id = request.data.get('track_id')

        if not track_id:
            return Response({'error': 'track_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            track_id = int(track_id)
            track = Track.objects.get(pk=track_id)
        except (ValueError, Track.DoesNotExist):
            return Response({'message': 'Track not found or already removed.'}, status=status.HTTP_200_OK)

        if not playlist.tracks.filter(pk=track.id).exists():
            return Response({'message': 'Track not in this playlist.'}, status=status.HTTP_200_OK)
            
        playlist.tracks.remove(track)
        return Response({'message': 'Track removed from playlist.'}, status=status.HTTP_200_OK)