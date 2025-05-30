from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status 
from rest_framework.response import Response
from django.utils import timezone
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload, ListenEvent 
from .serializers import (
    GenreSerializer, ArtistSerializer, ReleaseSerializer,
    TrackSerializer, CommentSerializer, HighlightSerializer,
    GeneratedDownloadRequestSerializer, GeneratedDownloadStatusSerializer,
    ListenSegmentLogSerializer 
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser, IsAuthenticated 
from rest_framework.filters import SearchFilter, OrderingFilter 
from django_filters.rest_framework import DjangoFilterBackend 

from music.permissions import IsOwnerOrReadOnly, CanViewTrack, CanEditTrack
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django.http import FileResponse, Http404, HttpResponseForbidden
import os
import mimetypes 
from django.db import models as django_models 
from django.db.models import Prefetch 
from django.db.models import F, Q 
from rest_framework.decorators import action, api_view, permission_classes as drf_permission_classes 
from rest_framework.permissions import IsAuthenticated as DRFIsAuthenticated 
import logging

from .tasks import generate_release_download_zip, process_listen_segment_task 

logger = logging.getLogger(__name__)


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all().order_by('name')
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['name']
    filterset_fields = ['name']


class ArtistViewSet(viewsets.ModelViewSet):
    queryset = Artist.objects.all()
    serializer_class = ArtistSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend] 
    search_fields = ['name', 'bio', 'location', 'user__username'] 
    ordering_fields = ['name'] 
    filterset_fields = ['location'] 
    
    def perform_create(self, serializer):
        if Artist.objects.filter(user=self.request.user).exists():
             raise ValidationError("You already have an associated artist profile.")
        serializer.save(user=self.request.user)

class ReleaseViewSet(viewsets.ModelViewSet):
    serializer_class = ReleaseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter] 
    filterset_fields = ['artist', 'genres', 'release_type', 'artist__name'] 
    search_fields = [
        'title', 
        'artist__name', 
        'tracks__title', 
        'genres__name'   
    ] 
    ordering_fields = ['release_date', 'listen_count', 'title'] 
    ordering = ['-release_date'] 

    def get_queryset(self):
        user = self.request.user
        
        prefetch_tracks_with_genres = Prefetch(
            'tracks',
            queryset=Track.objects.prefetch_related('genres')
        )

        base_queryset = Release.objects.select_related('artist').prefetch_related(
            'genres', prefetch_tracks_with_genres 
        )

        visible_to_all_q = django_models.Q(is_published=True, release_date__lte=timezone.now())
        
        if user.is_authenticated:
            if user.is_staff:
                queryset = base_queryset.all()
            else:
                user_artist_q = django_models.Q(artist__user=user)
                queryset = base_queryset.filter(visible_to_all_q | user_artist_q).distinct()
        else:
            queryset = base_queryset.filter(visible_to_all_q)
        
        return queryset

    def perform_create(self, serializer):
        try:
            artist = Artist.objects.get(user=self.request.user)
            serializer.save(artist=artist)
        except Artist.DoesNotExist:
            raise PermissionDenied("You must have an artist profile to create releases.")

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated]) 
    def request_download(self, request, pk=None):
        release = self.get_object() 

        can_download = False
        if release.pricing_model == Release.PricingModel.FREE:
            can_download = True
        elif request.user.is_authenticated and hasattr(release.artist, 'user') and release.artist.user and release.artist.user.id == request.user.id: 
            can_download = True
        
        if not can_download:
            if release.pricing_model in [Release.PricingModel.PAID, Release.PricingModel.NAME_YOUR_PRICE]:
                if not request.user.is_authenticated: 
                     return Response({"detail": "Authentication required to download priced items."}, status=status.HTTP_401_UNAUTHORIZED)
                from library.models import UserLibraryItem 
                if not UserLibraryItem.objects.filter(user=request.user, release=release).exists():
                     return Response({"detail": "You must own this release to download it."}, status=status.HTTP_403_FORBIDDEN)
                can_download = True 
            else: 
                return Response({"detail": "You do not have permission to download this release."}, status=status.HTTP_403_FORBIDDEN)
        
        if not can_download: 
             return Response({"detail": "Download conditions not met."}, status=status.HTTP_403_FORBIDDEN)


        request_serializer = GeneratedDownloadRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        requested_format = request_serializer.validated_data['requested_format']
        
        existing_ready_download = GeneratedDownload.objects.filter(
            release=release,
            user=request.user,
            requested_format=requested_format,
            status=GeneratedDownload.StatusChoices.READY,
            expires_at__gt=timezone.now() 
        ).first()

        if existing_ready_download:
            status_serializer = GeneratedDownloadStatusSerializer(existing_ready_download, context={'request': request})
            return Response(status_serializer.data, status=status.HTTP_200_OK)

        download_request = GeneratedDownload.objects.create(
            release=release,
            user=request.user,
            requested_format=requested_format,
            status=GeneratedDownload.StatusChoices.PENDING
        )

        generate_release_download_zip.delay(download_request.id)

        status_serializer = GeneratedDownloadStatusSerializer(download_request, context={'request': request})
        return Response(status_serializer.data, status=status.HTTP_202_ACCEPTED)


class TrackViewSet(viewsets.ModelViewSet):
    serializer_class = TrackSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    filterset_fields = ['release', 'genres', 'release__artist__name']
    search_fields = ['title', 'release__title', 'release__artist__name', 'genres__name']
    ordering_fields = ['track_number', 'title', 'listen_count', 'release__release_date']
    ordering = ['release__release_date', 'track_number']


    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'log_listen_segment': 
            permission_classes = [permissions.IsAuthenticated] 
        else: 
            permission_classes = [permissions.IsAuthenticatedOrReadOnly, CanViewTrack, CanEditTrack]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        qs = Track.objects.select_related(
            'release__artist', 
            'release__artist__user' 
        ).prefetch_related('genres')

        if self.action == 'list': 
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
        return qs 

    @action(detail=True, methods=['post'], serializer_class=ListenSegmentLogSerializer)
    def log_listen_segment(self, request, pk=None):
        track = self.get_object() 
        serializer = ListenSegmentLogSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        
        user_id_to_log = request.user.id 

        segment_start_timestamp_utc_iso = data['segment_start_timestamp_utc'].isoformat()
        segment_duration_ms = data['segment_duration_ms']
        
        process_listen_segment_task.delay(
            user_id_to_log, 
            track.id,
            segment_start_timestamp_utc_iso,
            segment_duration_ms
        )
            
        return Response(
            {'status': 'listen segment received and queued for processing'}, 
            status=status.HTTP_202_ACCEPTED
        )


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HighlightViewSet(viewsets.ReadOnlyModelViewSet): 
    serializer_class = HighlightSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        now = timezone.now()
        return Highlight.objects.filter(
            is_active=True,
            release__is_published=True, 
            release__release_date__lte=now, 
            display_start_datetime__lte=now
        ).filter(
            Q(display_end_datetime__isnull=True) | Q(display_end_datetime__gte=now)
        ).select_related(
            'release__artist' 
        ).prefetch_related(
            'release__genres', 
            Prefetch('release__tracks', queryset=Track.objects.prefetch_related('genres')) 
        ).order_by('order', '-display_start_datetime')


def stream_track_audio(request, track_id):
    print(f"--- stream_track_audio for track_id: {track_id} ---") 
    http_range = request.META.get('HTTP_RANGE')
    print(f"DEBUG: HTTP_RANGE header received: {http_range}") 

    track = get_object_or_404(Track, pk=track_id)
    
    can_stream = False
    release = track.release
    if request.user and request.user.is_staff:
        can_stream = True
    elif request.user and request.user.is_authenticated:
        try:
            user_artist = Artist.objects.get(user=request.user) 
            if release.artist_id == user_artist.id: 
                can_stream = True
        except Artist.DoesNotExist:
            pass 
    
    if not can_stream and release.is_published and release.release_date <= timezone.now():
        can_stream = True
            
    if not can_stream:
        print(f"DEBUG: Permission denied for track {track_id}. User: {request.user}") 
        raise Http404("Track not found or you do not have permission to stream it.")

    if not track.audio_file:
        print(f"DEBUG: No audio_file attribute for track {track_id}.") 
        raise Http404("Audio file not found for this track.")
    if not track.audio_file.storage.exists(track.audio_file.name):
        print(f"DEBUG: Audio file '{track.audio_file.name}' does not exist in storage.") 
        raise Http404("Audio file path does not exist in storage.")

    try:
        file_to_serve = track.audio_file.open('rb')
        print(f"DEBUG: Opened file '{track.audio_file.name}' for streaming.") 
        
        content_type, encoding = mimetypes.guess_type(track.audio_file.name)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        if track.audio_file.name.lower().endswith('.wav') and content_type == 'audio/x-wav':
            content_type = 'audio/wav'
        print(f"DEBUG: Serving with Content-Type: {content_type}") 

        response = FileResponse(file_to_serve, content_type=content_type, as_attachment=False)
        response['Accept-Ranges'] = 'bytes'
        
        print(f"DEBUG: FileResponse created. Accept-Ranges: {response.get('Accept-Ranges')}") 
        
        return response
    except FileNotFoundError:
        print(f"DEBUG: FileNotFoundError for track {track_id} (should have been caught by storage.exists).") 
        raise Http404("Audio file not found on the server's filesystem.")
    except Exception as e:
        print(f"ERROR serving audio file for track {track_id}: {e}") 
        import traceback
        traceback.print_exc()
        raise Http404("An error occurred while trying to serve the audio file.")

class GeneratedDownloadStatusViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = GeneratedDownloadStatusSerializer
    permission_classes = [IsAuthenticated] 

    def get_queryset(self):
        return GeneratedDownload.objects.filter(user=self.request.user).select_related('release')
    

@api_view(['GET']) 
@drf_permission_classes([DRFIsAuthenticated]) 
def serve_generated_download_file(request, download_uuid):
    logger.info(f"serve_generated_download_file: User {request.user.username} (ID: {request.user.id}) attempting to download UUID {download_uuid}")

    try:
        download_request = GeneratedDownload.objects.select_related('user').get(
            unique_identifier=download_uuid
        )
        if download_request.user_id != request.user.id:
            logger.warning(f"serve_generated_download_file: User {request.user.username} (ID: {request.user.id}) "
                           f"attempted to access download UUID {download_uuid} belonging to user ID {download_request.user_id}. Forbidden.")
            return Response({"detail": "Download link not found or invalid (permission denied)."}, status=status.HTTP_403_FORBIDDEN)

    except GeneratedDownload.DoesNotExist:
        logger.warning(f"serve_generated_download_file: Download UUID {download_uuid} not found in database.")
        return Response({"detail": "Download link not found or invalid."}, status=status.HTTP_404_NOT_FOUND)

    logger.info(f"serve_generated_download_file: Found DownloadRequest ID {download_request.id} for UUID {download_uuid}, status: {download_request.status}")

    if download_request.status != GeneratedDownload.StatusChoices.READY:
        logger.warning(f"serve_generated_download_file: Download ID {download_request.id} is not READY (status: {download_request.status}).")
        return Response({"detail": "Download is not ready or has failed."}, status=status.HTTP_404_NOT_FOUND)
    
    if download_request.expires_at and download_request.expires_at < timezone.now():
        logger.info(f"serve_generated_download_file: Download ID {download_request.id} has expired (expires_at: {download_request.expires_at}).")
        download_request.status = GeneratedDownload.StatusChoices.EXPIRED
        download_request.save(update_fields=['status'])
        return Response({"detail": "This download link has expired."}, status=status.HTTP_410_GONE) 

    if not download_request.download_file or not download_request.download_file.name:
        logger.error(f"serve_generated_download_file: No file associated with Download ID {download_request.id}.")
        return Response({"detail": "File not available for this download record."}, status=status.HTTP_404_NOT_FOUND)

    if not download_request.download_file.storage.exists(download_request.download_file.name):
        logger.error(f"File for GeneratedDownload ID {download_request.id} not found in storage at {download_request.download_file.name}")
        download_request.status = GeneratedDownload.StatusChoices.FAILED
        download_request.failure_reason = "File missing from storage."
        download_request.save()
        return Response({"detail": "File is missing. Please try generating the download again."}, status=status.HTTP_404_NOT_FOUND)

    try:
        logger.info(f"serve_generated_download_file: Serving file {download_request.download_file.name} for Download ID {download_request.id}.")
        response = FileResponse(download_request.download_file.open('rb'), as_attachment=True)
        return response
    except FileNotFoundError: 
        logger.error(f"FileNotFound (physical file) for GeneratedDownload ID {download_request.id} at {getattr(download_request.download_file, 'path', 'N/A')}")
        download_request.status = GeneratedDownload.StatusChoices.FAILED
        download_request.failure_reason = "File could not be opened from storage (FileNotFound)."
        download_request.save()
        return Response({"detail": "Error serving the file. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        logger.exception(f"Unexpected error serving generated download {download_request.id}: {e}")
        return Response({"detail": "An unexpected error occurred while preparing your download."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)