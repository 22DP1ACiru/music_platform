from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import Playlist
from .serializers import PlaylistSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly

class PlaylistViewSet(viewsets.ModelViewSet):
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] # Must be logged in to create/edit

    # Ensure users only see their own playlists + public ones,
    # and can only edit their own.
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Show user's own playlists OR public ones
            return Playlist.objects.filter(
                models.Q(owner=user) | models.Q(is_public=True)
            ).select_related('owner').prefetch_related('tracks').distinct() # Optimization & avoid duplicates
        else:
            # Anonymous users only see public playlists
            return Playlist.objects.filter(is_public=True).select_related('owner').prefetch_related('tracks')

    # Automatically set owner on creation
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
