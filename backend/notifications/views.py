from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly for now
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Filter by is_artist_channel based on a query parameter
        is_artist_channel_query = self.request.query_params.get('artist_channel', None)
        
        queryset = Notification.objects.filter(recipient=user)
        
        if is_artist_channel_query is not None:
            if is_artist_channel_query.lower() == 'true':
                queryset = queryset.filter(is_artist_channel=True)
            elif is_artist_channel_query.lower() == 'false':
                queryset = queryset.filter(is_artist_channel=False)
        
        return queryset.select_related(
            'actor_user', 'actor_artist',
            'target_release', 'target_artist_profile', 'target_user_profile',
            'target_conversation', 'target_order'
        ).order_by('-created_at')

    @action(detail=False, methods=['post'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        is_artist_channel_query = self.request.query_params.get('artist_channel', None)
        qs_to_update = Notification.objects.filter(recipient=request.user, is_read=False)
        
        if is_artist_channel_query is not None:
            if is_artist_channel_query.lower() == 'true':
                qs_to_update = qs_to_update.filter(is_artist_channel=True)
            elif is_artist_channel_query.lower() == 'false':
                qs_to_update = qs_to_update.filter(is_artist_channel=False)
        
        updated_count = qs_to_update.update(is_read=True)
        return Response({'message': f'{updated_count} notifications marked as read.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        if notification.recipient != request.user:
            return Response({'detail': 'Not authorized.'}, status=status.HTTP_403_FORBIDDEN)
        
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        user = request.user
        is_artist_channel_query = self.request.query_params.get('artist_channel', None)
        
        user_channel_count_qs = Notification.objects.filter(recipient=user, is_read=False, is_artist_channel=False)
        artist_channel_count_qs = Notification.objects.filter(recipient=user, is_read=False, is_artist_channel=True)

        response_data = {
            'user_channel_unread_count': user_channel_count_qs.count(),
            'artist_channel_unread_count': artist_channel_count_qs.count(),
            'total_unread_count': user_channel_count_qs.count() + artist_channel_count_qs.count()
        }
        
        if is_artist_channel_query is not None:
            if is_artist_channel_query.lower() == 'true':
                response_data['requested_channel_unread_count'] = artist_channel_count_qs.count()
            elif is_artist_channel_query.lower() == 'false':
                response_data['requested_channel_unread_count'] = user_channel_count_qs.count()
        
        return Response(response_data)