from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import UserLibraryItem
from music.models import Release, GeneratedDownload 
from .serializers import UserLibraryItemSerializer, AddToLibrarySerializer

from music.serializers import GeneratedDownloadRequestSerializer, GeneratedDownloadStatusSerializer
from music.tasks import generate_release_download_zip


class LibraryViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserLibraryItem.objects.filter(user=self.request.user)\
            .select_related('release__artist')\
            .prefetch_related(
                'release__genres', 
                'release__tracks__genres' 
            )


    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = UserLibraryItemSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='add-item', serializer_class=AddToLibrarySerializer)
    def add_item_to_library(self, request):
        print(f"DEBUG: add_item_to_library received data: {request.data}") 

        serializer = AddToLibrarySerializer(data=request.data)
        if serializer.is_valid():
            release_id = serializer.validated_data['release_id']
            # Default to FREE if not provided, or if you want to enforce only FREE additions here.
            # For purchased items, they should be added via the order completion signal/logic.
            acquisition_type = serializer.validated_data.get('acquisition_type', UserLibraryItem.ACQUISITION_CHOICES[0][0]) # Default to FREE

            try:
                release_to_add = Release.objects.get(pk=release_id)
            except Release.DoesNotExist: 
                return Response({'detail': 'Release not found.'}, status=status.HTTP_404_NOT_FOUND)

            can_acquire = release_to_add.is_visible()
            if request.user.is_authenticated and hasattr(release_to_add.artist, 'user') and release_to_add.artist.user == request.user:
                 can_acquire = True 
            if request.user.is_staff:
                 can_acquire = True
            
            # Ensure only FREE items or items by the artist themselves can be added via this specific endpoint
            # if acquisition_type != UserLibraryItem.ACQUISITION_CHOICES[0][0] and not (hasattr(release_to_add.artist, 'user') and release_to_add.artist.user == request.user):
            #     print(f"DEBUG: add_item_to_library - Attempt to add non-FREE item {release_id} via generic add. Acquisition type: {acquisition_type}")
            #     return Response({'detail': 'Priced items are added to library upon acquisition.'}, status=status.HTTP_400_BAD_REQUEST)


            if not can_acquire :
                print(f"DEBUG: add_item_to_library - can_acquire is False for release {release_id}. is_visible: {release_to_add.is_visible()}")
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
                # If item already exists, and type is different (e.g. was FREE, now acquired as PURCHASED), update it.
                # This might be better handled by the order creation logic itself ensuring the correct type.
                # For this endpoint, if it exists, we probably don't want to change its acquisition_type here
                # unless it's a specific scenario (e.g., upgrading a FREE to PURCHASED if logic allows).
                # For now, if it exists, and the type is different, we could update it, or just return the existing.
                if library_item.acquisition_type != acquisition_type and acquisition_type == UserLibraryItem.ACQUISITION_CHOICES[0][0]: 
                    # Only allow updating to FREE here if it was something else and now it's explicitly being added as FREE.
                    # This is a bit complex, might be simpler to not change type here.
                    pass # For now, don't change if it exists through this specific 'add-item' endpoint,
                         # as purchases/NYP handle their own library addition.
                
                item_serializer = UserLibraryItemSerializer(library_item, context={'request': request})
                return Response(item_serializer.data, status=status.HTTP_200_OK)
        else:
            print(f"DEBUG: AddToLibrarySerializer errors: {serializer.errors}") 
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'], url_path='remove-item') 
    def remove_item_from_library(self, request, pk=None): 
        library_item = get_object_or_404(UserLibraryItem, pk=pk, user=request.user)
        
        # Check acquisition type. Prevent deletion if 'PURCHASED' or 'NYP'.
        # Allow deletion if 'FREE'.
        if library_item.acquisition_type == UserLibraryItem.ACQUISITION_CHOICES[0][0]: # 'FREE'
            library_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        elif library_item.acquisition_type in [UserLibraryItem.ACQUISITION_CHOICES[1][0], UserLibraryItem.ACQUISITION_CHOICES[2][0]]: # 'PURCHASED' or 'NYP'
            return Response(
                {'detail': 'Purchased items cannot be removed from your library.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            # For any other acquisition types you might add in the future, decide on the policy.
            # As a default, let's be restrictive.
            return Response(
                {'detail': 'This item cannot be removed from your library at this time.'},
                status=status.HTTP_403_FORBIDDEN
            )

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