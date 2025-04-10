from django.shortcuts import render
from rest_framework import viewsets, permissions, generics
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import UserProfile
from .serializers import UserSerializer, UserProfileSerializer, RegisterSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from music.permissions import IsOwnerOrReadOnly

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Return the details of the currently authenticated user.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows user profiles to be viewed or edited.
    """
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    serializer_class = UserProfileSerializer

    @action(detail=False, methods=['get', 'put', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        # Get the profile associated with the requesting user
        # Use get_object_or_404 for cleaner error handling if profile doesn't exist
        from django.shortcuts import get_object_or_404
        profile = get_object_or_404(UserProfile, user=request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        elif request.method in ['PUT', 'PATCH']:
            # Use partial=True for PATCH to allow partial updates
            serializer = self.get_serializer(profile, data=request.data, partial=(request.method == 'PATCH'))
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
    
class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,) # Anyone can register
    serializer_class = RegisterSerializer