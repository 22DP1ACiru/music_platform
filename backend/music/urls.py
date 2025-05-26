from django.urls import path
from .views import serve_generated_download_file

# These are for non-router paths within the music app.
# Router paths are handled in the main vaultwave/urls.py

urlpatterns = [
    path('generated-downloads/<uuid:download_uuid>/file/', serve_generated_download_file, name='generated-download-file'),
    # Example:
    # path('some-other-music-feature/', some_view_function, name='some-feature'),
]