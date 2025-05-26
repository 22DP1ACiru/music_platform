from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.utils import timezone
from .models import Genre, Artist, Release, Track, Comment, Highlight, GeneratedDownload # Ensure 'models' is imported
from .serializers import (
    GenreSerializer, ArtistSerializer, ReleaseSerializer,
    TrackSerializer, CommentSerializer, HighlightSerializer,
    GeneratedDownloadRequestSerializer, GeneratedDownloadStatusSerializer # New serializers
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAdminUser, IsAuthenticated
from music.permissions import IsOwnerOrReadOnly, CanViewTrack, CanEditTrack
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from django.http import FileResponse, Http404, HttpResponseForbidden
import os
import mimetypes 
from django.db import models as django_models # Explicit import for Q objects
from rest_framework.decorators import action # For custom actions

# Import the Celery task
from .tasks import generate_release_download_zip


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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def request_download(self, request, pk=None):
        release = self.get_object() # Checks IsOwnerOrReadOnly for SAFE_METHODS, but we need specific logic for download access

        # --- Download Permission Logic (Placeholder - needs refinement) ---
        # For now, allow if the release is FREE, or user is owner.
        # TODO: Integrate with actual purchase/entitlement check later.
        can_download = False
        if release.pricing_model == Release.PricingModel.FREE:
            can_download = True
        elif request.user.is_authenticated and release.artist.user == request.user: # Owner can download
            can_download = True
        # Add logic here for:
        # - User has purchased this release (check OrderItem for this user and release).
        # - User has an active subscription that grants download access.
        
        if not can_download:
             # Simulate a purchase check for PAID or NYP for now
            if release.pricing_model in [Release.PricingModel.PAID, Release.PricingModel.NAME_YOUR_PRICE]:
                # This is a placeholder. Real check would be against orders.
                # For testing, let's allow if authenticated for now on priced items.
                if not request.user.is_authenticated:
                     return Response({"detail": "Authentication required to download priced items."}, status=status.HTTP_401_UNAUTHORIZED)
                # Here, you'd check if request.user has bought it.
                # If not, return something like:
                # return Response({"detail": "You must purchase this release to download it."}, status=status.HTTP_403_FORBIDDEN)
            else: # Should not happen if logic above is complete
                return Response({"detail": "You do not have permission to download this release."}, status=status.HTTP_403_FORBIDDEN)


        request_serializer = GeneratedDownloadRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        requested_format = request_serializer.validated_data['requested_format']
        # quality_options = request_serializer.validated_data.get('quality_options') # If added

        # Check for existing recent, non-expired, READY requests for this user, release, format
        # to avoid re-generating too frequently.
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

        # Create a new download request record
        download_request = GeneratedDownload.objects.create(
            release=release,
            user=request.user,
            requested_format=requested_format,
            # quality_options=quality_options, # If added
            status=GeneratedDownload.StatusChoices.PENDING
        )

        # Trigger Celery task
        generate_release_download_zip.delay(download_request.id)

        status_serializer = GeneratedDownloadStatusSerializer(download_request, context={'request': request})
        return Response(status_serializer.data, status=status.HTTP_202_ACCEPTED)


class TrackViewSet(viewsets.ModelViewSet):
    serializer_class = TrackSerializer
    filterset_fields = ['release', 'genres']

    def get_permissions(self):
        if self.action == 'list':
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        elif self.action == 'create':
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
    
    if not can_stream: 
        if release.is_published and release.release_date <= timezone.now():
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

# --- Views for Generated Downloads ---
class GeneratedDownloadStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet to check the status of a generated download.
    Users can only access their own download requests.
    """
    serializer_class = GeneratedDownloadStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Ensure users can only see their own download requests
        return GeneratedDownload.objects.filter(user=self.request.user).select_related('release')
    
    # Optional: retrieve by unique_identifier instead of pk
    # lookup_field = 'unique_identifier' 
    # lookup_url_kwarg = 'download_uuid'


def serve_generated_download_file(request, download_uuid):
    """
    Serves the generated ZIP file.
    Authenticates the user and checks if the download belongs to them and is ready/not expired.
    """
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required.")

    try:
        download_request = GeneratedDownload.objects.get(
            unique_identifier=download_uuid,
            user=request.user
        )
    except GeneratedDownload.DoesNotExist:
        raise Http404("Download link not found or invalid.")

    if download_request.status != GeneratedDownload.StatusChoices.READY:
        raise Http404("Download is not ready or has failed.")
    
    if download_request.expires_at and download_request.expires_at < timezone.now():
        download_request.status = GeneratedDownload.StatusChoices.EXPIRED
        download_request.save(update_fields=['status'])
        # Optionally delete the file here if desired upon expiry access attempt
        # if download_request.download_file:
        #     download_request.download_file.delete(save=False)
        raise Http404("This download link has expired.")

    if not download_request.download_file or not download_request.download_file.name:
        raise Http404("File not available for this download record.")

    if not download_request.download_file.storage.exists(download_request.download_file.name):
        logger.error(f"File for GeneratedDownload ID {download_request.id} not found in storage at {download_request.download_file.name}")
        download_request.status = GeneratedDownload.StatusChoices.FAILED
        download_request.failure_reason = "File missing from storage."
        download_request.save()
        raise Http404("File is missing. Please try generating the download again.")

    try:
        # Using FileResponse to serve the file
        response = FileResponse(download_request.download_file.open('rb'), as_attachment=True)
        # Set content type if known, though browser might infer from extension
        response['Content-Type'] = 'application/zip' 
        # Content-Disposition is handled by as_attachment=True to suggest filename
        return response
    except FileNotFoundError:
        logger.error(f"FileNotFound (physical file) for GeneratedDownload ID {download_request.id} at {download_request.download_file.path if hasattr(download_request.download_file, 'path') else 'N/A'}")
        download_request.status = GeneratedDownload.StatusChoices.FAILED
        download_request.failure_reason = "File could not be opened from storage."
        download_request.save()
        raise Http404("Error serving the file. Please try again.")
    except Exception as e:
        logger.exception(f"Unexpected error serving generated download {download_request.id}: {e}")
        raise Http404("An unexpected error occurred while preparing your download.")