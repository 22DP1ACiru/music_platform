from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import UserLibraryItem
from music.models import Release, GeneratedDownload # Import Release and GeneratedDownload models
from .serializers import UserLibraryItemSerializer, AddToLibrarySerializer

# Import necessary serializers and tasks from the music app
from music.serializers import GeneratedDownloadRequestSerializer, GeneratedDownloadStatusSerializer
from music.tasks import generate_release_download_zip


class LibraryViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Returns UserLibraryItems for the current user
        # Optimized prefetching for nested ReleaseSerializer
        return UserLibraryItem.objects.filter(user=self.request.user)\
            .select_related('release__artist')\
            .prefetch_related(
                'release__genres', 
                'release__tracks__genres' 
            )


    def list(self, request, *args, **kwargs):
        """
        List all items in the current user's library.
        """
        queryset = self.get_queryset()
        serializer = UserLibraryItemSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-item', serializer_class=AddToLibrarySerializer)
    def add_item_to_library(self, request):
        """
        Add a release to the user's library.
        Expects {'release_id': <id>, 'acquisition_type': <type (optional)>}
        """
        print(f"DEBUG: add_item_to_library received data: {request.data}") # DEBUG LINE

        serializer = AddToLibrarySerializer(data=request.data)
        if serializer.is_valid():
            release_id = serializer.validated_data['release_id']
            acquisition_type = serializer.validated_data.get('acquisition_type', UserLibraryItem.ACQUISITION_CHOICES[0][0]) 

            try:
                release_to_add = Release.objects.get(pk=release_id)
            except Release.DoesNotExist: 
                return Response({'detail': 'Release not found.'}, status=status.HTTP_404_NOT_FOUND)

            can_acquire = release_to_add.is_visible()
            if request.user.is_authenticated and hasattr(release_to_add.artist, 'user') and release_to_add.artist.user == request.user:
                 can_acquire = True 
            if request.user.is_staff:
                 can_acquire = True

            if not can_acquire :
                print(f"DEBUG: add_item_to_library - can_acquire is False for release {release_id}. is_visible: {release_to_add.is_visible()}") # DEBUG LINE
                return Response({'detail': 'This release cannot be added to the library at this time.'}, status=status.HTTP_400_BAD_REQUEST)

            library_item, created = UserLibraryItem.objects.get_or_create(
                user=request.user,
                release=release_to_add,
                defaults={'acquisition_type': acquisition_type}
            )

            if created:
                item_serializer = UserLibraryItemSerializer(library_item, context={'request': request})
                return Response(item_serializer.data, status=status.HTTP_201_CREATED)
            else:
                if library_item.acquisition_type != acquisition_type: 
                    library_item.acquisition_type = acquisition_type 
                    library_item.save(update_fields=['acquisition_type'])

                item_serializer = UserLibraryItemSerializer(library_item, context={'request': request})
                return Response(item_serializer.data, status=status.HTTP_200_OK)
        else:
            print(f"DEBUG: AddToLibrarySerializer errors: {serializer.errors}") # DEBUG LINE
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-item') 
    def remove_item_from_library(self, request, pk=None): 
        library_item = get_object_or_404(UserLibraryItem, pk=pk, user=request.user)
        library_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], url_path='request-download') 
    def request_library_item_download(self, request, pk=None):
        library_item = get_object_or_404(UserLibraryItem, pk=pk, user=request.user)
        release_to_download = library_item.release

        request_serializer = GeneratedDownloadRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        requested_format = request_serializer.validated_data['requested_format']

        existing_ready_download = GeneratedDownload.objects.filter(
            release=release_to_download,
            user=request.user,
            requested_format=requested_format,
            status=GeneratedDownload.StatusChoices.READY,
            expires_at__gt=timezone.now()
        ).first()

        if existing_ready_download:
            status_serializer = GeneratedDownloadStatusSerializer(existing_ready_download, context={'request': request})
            return Response(status_serializer.data, status=status.HTTP_200_OK)

        download_request_instance = GeneratedDownload.objects.create(
            release=release_to_download,
            user=request.user,
            requested_format=requested_format,
            status=GeneratedDownload.StatusChoices.PENDING
        )

        generate_release_download_zip.delay(download_request_instance.id)

        status_serializer = GeneratedDownloadStatusSerializer(download_request_instance, context={'request': request})
        return Response(status_serializer.data, status=status.HTTP_202_ACCEPTED)