from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from music.models import Artist, Release, Track, ListenEvent, Genre # ADD ListenEvent, Genre
from interactions.models import Follow
from shop.models import OrderItem, Order
from .serializers import (
    ArtistDashboardStatsSerializer, 
    UserListeningHabitsSerializer, # New Import
    # Other imports might not be directly used as arguments here
    # UserListenedTrackStatSerializer, # Will be used by UserListeningHabitsSerializer
    # UserListenedArtistStatSerializer,
    # UserListenedGenreStatSerializer
)

class ArtistStatsViewSet(viewsets.ViewSet): 
    permission_classes = [permissions.IsAuthenticated]

    def get_artist_profile(self, request):
        try:
            return request.user.artist_profile 
        except Artist.DoesNotExist:
            return None
        except AttributeError: 
             return None

    @action(detail=False, methods=['get'], url_path='my-dashboard')
    def my_dashboard_stats(self, request):
        artist_profile = self.get_artist_profile(request)
        if not artist_profile:
            return Response({"detail": "Artist profile not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        period_param = request.query_params.get('period', 'all_time')
        now = timezone.now()
        start_date = None

        if period_param == '7days':
            start_date = now - timedelta(days=7)
        elif period_param == '30days':
            start_date = now - timedelta(days=30)
        
        total_release_listens_agg = Release.objects.filter(artist=artist_profile).aggregate(total=Sum('listen_count'))
        total_release_listens = total_release_listens_agg['total'] or 0
        
        total_track_listens_agg = Track.objects.filter(release__artist=artist_profile).aggregate(total=Sum('listen_count'))
        total_track_listens = total_track_listens_agg['total'] or 0
        
        order_items_query = OrderItem.objects.filter(
            order__status=Order.ORDER_STATUS_CHOICES[2][0], 
            product__release__artist=artist_profile,
            product__release__isnull=False 
        )
        if start_date:
            order_items_query = order_items_query.filter(order__created_at__gte=start_date)

        total_sales_count = order_items_query.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        
        total_sales_value_usd_agg = order_items_query.aggregate(
            total_revenue=Sum(F('quantity') * F('price_at_purchase'))
        )
        total_sales_value_usd = total_sales_value_usd_agg['total_revenue'] or Decimal('0.00')

        current_follower_count = Follow.objects.filter(artist=artist_profile).count()

        summary_data = {
            'total_release_listens': total_release_listens,
            'total_track_listens': total_track_listens,
            'total_sales_count': total_sales_count,
            'total_sales_value_usd': total_sales_value_usd,
            'current_follower_count': current_follower_count,
        }
        
        top_releases_qs = Release.objects.filter(artist=artist_profile).order_by('-listen_count')[:5]
        top_tracks_qs = Track.objects.filter(release__artist=artist_profile).order_by('-listen_count')[:5]

        dashboard_data_for_serializer = {
            'summary': summary_data, 
            'top_releases': top_releases_qs, 
            'top_tracks': top_tracks_qs,     
        }
        
        final_serializer = ArtistDashboardStatsSerializer(
            instance=dashboard_data_for_serializer, 
            context={'request': request}
        )
        return Response(final_serializer.data)


class UserStatsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='my-listening-habits')
    def my_listening_habits(self, request):
        user = request.user
        
        period_param = request.query_params.get('period', 'all_time')
        limit_param = int(request.query_params.get('limit', 5)) # How many top items to return
        now = timezone.now()
        start_date = None

        if period_param == '7days':
            start_date = now - timedelta(days=7)
        elif period_param == '30days':
            start_date = now - timedelta(days=30)

        # Base query for user's listen events within the period
        listen_events_query = ListenEvent.objects.filter(user=user)
        if start_date:
            listen_events_query = listen_events_query.filter(listened_at__gte=start_date)

        # 1. Top Listened Tracks by this User
        top_listened_tracks_data = listen_events_query.values(
            'track_id', 
            'track__title', 
            'track__duration_in_seconds',
            'track__release__title', 
            'track__release__artist__name',
            'track__release__artist__id',
            'track__release__id',
            'track__release__cover_art'
        ).annotate(
            user_listen_count=Count('track_id')
        ).order_by('-user_listen_count')[:limit_param]

        # Manually construct track objects for the serializer due to grouped/annotated data
        # This is because .values() returns dicts, not model instances.
        top_tracks_for_serializer = []
        for item in top_listened_tracks_data:
            top_tracks_for_serializer.append({
                'id': item['track_id'],
                'title': item['track__title'],
                'duration_in_seconds': item['track__duration_in_seconds'],
                'release_title': item['track__release__title'],
                'artist_name': item['track__release__artist__name'],
                'artist_id': item['track__release__artist__id'],
                'release_id': item['track__release__id'],
                'cover_art': item['track__release__cover_art'], # This will be path, serializer handles full URL
                'user_listen_count': item['user_listen_count']
            })
        
        # 2. Top Listened Artists by this User
        top_listened_artists_data = listen_events_query.values(
            'track__release__artist_id', 
            'track__release__artist__name',
            'track__release__artist__artist_picture', # Assuming artist_picture is on Artist model
            'track__release__artist__user_id' # Assuming user_id is on Artist model for ArtistSerializer compatibility
        ).annotate(
            user_listen_count_for_artist=Count('track__release__artist_id')
        ).order_by('-user_listen_count_for_artist').filter(track__release__artist_id__isnull=False)[:limit_param]

        top_artists_for_serializer = []
        for item in top_listened_artists_data:
            top_artists_for_serializer.append({
                'id': item['track__release__artist_id'],
                'name': item['track__release__artist__name'],
                'artist_picture': item['track__release__artist__artist_picture'],
                'user_id': item['track__release__artist__user_id'], # For FullArtistSerializer if it needs user
                'user_listen_count_for_artist': item['user_listen_count_for_artist']
                # Add other fields if your UserListenedArtistStatSerializer expects them from FullArtistSerializer
            })

        # 3. Top Listened Genres by this User
        # This is a bit more complex as genres are M2M on Track
        # We'll count listen events for tracks that belong to each genre
        top_listened_genres_data = listen_events_query.filter(
            track__genres__isnull=False # Only consider tracks that have genres
        ).values(
            'track__genres__id', 
            'track__genres__name'
        ).annotate(
            user_listen_count_for_genre=Count('track__genres__id')
        ).order_by('-user_listen_count_for_genre')[:limit_param]

        top_genres_for_serializer = []
        for item in top_listened_genres_data:
            top_genres_for_serializer.append({
                'id': item['track__genres__id'],
                'name': item['track__genres__name'],
                'user_listen_count_for_genre': item['user_listen_count_for_genre']
            })
        
        # 4. Total listen events (significant listens)
        total_listen_events_count = listen_events_query.count()

        user_habits_data = {
            'top_listened_tracks': top_tracks_for_serializer,
            'top_listened_artists': top_artists_for_serializer,
            'top_listened_genres': top_genres_for_serializer,
            'total_listen_events_count': total_listen_events_count,
        }

        serializer = UserListeningHabitsSerializer(instance=user_habits_data, context={'request': request})
        return Response(serializer.data)