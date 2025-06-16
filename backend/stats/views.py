from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Sum, Count, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from music.models import Artist, Release, Track
from interactions.models import Follow
from shop.models import OrderItem, Order
from .serializers import (
    ArtistDashboardStatsSerializer, 
    # ArtistBasicStatsSerializer, # Not directly used as an argument here
    # ArtistTopReleaseStatSerializer, # Not directly used as an argument here
    # ArtistTopTrackStatSerializer  # Not directly used as an argument here
)
# from shop.constants import ORDER_SETTLEMENT_CURRENCY 


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

        # MODIFIED: Pass querysets/lists of instances directly
        dashboard_data_for_serializer = {
            'summary': summary_data, 
            'top_releases': top_releases_qs, # Pass the queryset/list of instances
            'top_tracks': top_tracks_qs,     # Pass the queryset/list of instances
        }
        
        # Instantiate the main serializer and pass the context
        final_serializer = ArtistDashboardStatsSerializer(
            instance=dashboard_data_for_serializer, # Use 'instance' when passing model instances or dicts for read-only
            context={'request': request} # Crucial for generating full URLs for images/files
        )
        # No need for final_serializer.is_valid() when using 'instance=' for read-only operations.
        # is_valid() is for validating incoming data for write operations.

        return Response(final_serializer.data)