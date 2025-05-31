from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Follow
from music.models import Artist
from .serializers import FollowSerializer, FollowerSerializer, FollowingSerializer
from django.contrib.auth.models import User # <--- CORRECTED IMPORT

class FollowViewSet(viewsets.GenericViewSet): # Not ModelViewSet for custom actions
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FollowSerializer # Default serializer

    def get_queryset(self):
        # This is mainly for DRF schema generation, specific actions will have their own queries
        return Follow.objects.all()

    @action(detail=False, methods=['post'], url_path='follow-artist')
    def follow_artist(self, request):
        """
        Follow an artist. Requires 'artist_id' in request data.
        """
        artist_id = request.data.get('artist_id')
        if not artist_id:
            return Response({"artist_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        artist_to_follow = get_object_or_404(Artist, pk=artist_id)
        
        if artist_to_follow.user == request.user:
            return Response({"detail": "You cannot follow your own artist profile."}, status=status.HTTP_400_BAD_REQUEST)

        follow, created = Follow.objects.get_or_create(user=request.user, artist=artist_to_follow)

        if created:
            # TODO: Create a notification for the followed artist
            return Response(FollowSerializer(follow, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response({"detail": "You are already following this artist."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='unfollow-artist')
    def unfollow_artist(self, request):
        """
        Unfollow an artist. Requires 'artist_id' in request data.
        """
        artist_id = request.data.get('artist_id')
        if not artist_id:
            return Response({"artist_id": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        artist_to_unfollow = get_object_or_404(Artist, pk=artist_id)
        
        try:
            follow_instance = Follow.objects.get(user=request.user, artist=artist_to_unfollow)
            follow_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Follow.DoesNotExist:
            return Response({"detail": "You are not following this artist."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='followers', permission_classes=[permissions.AllowAny]) # Artist's followers (pk is artist_id)
    def list_followers(self, request, pk=None):
        """
        List users following a specific artist.
        """
        artist = get_object_or_404(Artist, pk=pk)
        followers = Follow.objects.filter(artist=artist).select_related('user__profile')
        page = self.paginate_queryset(followers)
        if page is not None:
            serializer = FollowerSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = FollowerSerializer(followers, many=True, context={'request': request})
        return Response(serializer.data)
        
    @action(detail=True, methods=['get'], url_path='following', permission_classes=[permissions.AllowAny]) # Artists followed by a user (pk is user_id)
    def list_following(self, request, pk=None):
        """
        List artists a specific user is following.
        """
        user = get_object_or_404(User, pk=pk)
        following = Follow.objects.filter(user=user).select_related('artist')
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = FollowingSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = FollowingSerializer(following, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='my-following')
    def list_my_following(self, request):
        """List artists the authenticated user is following."""
        user = request.user
        following = Follow.objects.filter(user=user).select_related('artist')
        page = self.paginate_queryset(following)
        if page is not None:
            serializer = FollowingSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = FollowingSerializer(following, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='is-following', permission_classes=[permissions.IsAuthenticated])
    def is_following(self, request, pk=None): # pk here is artist_id
        """Check if the authenticated user is following a specific artist."""
        artist = get_object_or_404(Artist, pk=pk)
        is_following = Follow.objects.filter(user=request.user, artist=artist).exists()
        return Response({'is_following': is_following})