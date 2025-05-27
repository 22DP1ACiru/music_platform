// frontend/src/views/ArtistDetailView.vue
<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import ArtistEditForm from "@/components/ArtistEditForm.vue";

// --- Interfaces ---
interface ArtistDetail {
  id: number;
  name: string;
  bio: string | null;
  artist_picture: string | null; // URL
  location: string | null;
  website_url: string | null;
  user: string; // Username (from StringRelatedField)
  user_id: number; // User ID (from ReadOnlyField)
}

// Interface for individual release items within the paginated response
interface ReleaseSummary {
  id: number;
  title: string;
  cover_art: string | null;
  release_type: string;
  // Add release_type_display if your backend serializer for this view includes it
  release_type_display?: string;
}

// Interface for the paginated response from /releases/?artist=ID
interface PaginatedArtistReleasesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ReleaseSummary[];
}

// --- Props ---
const props = defineProps<{
  id: string;
}>();

const authStore = useAuthStore();
const router = useRouter();
const artist = ref<ArtistDetail | null>(null);
const releases = ref<ReleaseSummary[]>([]); // This will hold the array of ReleaseSummary
const isLoadingArtist = ref(true);
const isLoadingReleases = ref(true);
const error = ref<string | null>(null);
const isEditing = ref(false);
const editError = ref<string | null>(null);

const isOwner = computed(() => {
  return (
    authStore.isLoggedIn &&
    authStore.authUser &&
    artist.value &&
    artist.value.user_id === authStore.authUser.id
  );
});

const fetchArtistDetail = async (artistId: string) => {
  isLoadingArtist.value = true;
  error.value = null;
  artist.value = null;
  try {
    console.log(`Fetching artist details for ID: ${artistId}`);
    const response = await axios.get<ArtistDetail>(`/artists/${artistId}/`);
    artist.value = response.data;
  } catch (err: any) {
    console.error(`Failed to fetch artist ${artistId}:`, err);
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Artist not found.";
    } else {
      error.value = "Could not load artist details.";
    }
  } finally {
    isLoadingArtist.value = false;
  }
};

const fetchArtistReleases = async (artistId: string) => {
  isLoadingReleases.value = true;
  releases.value = []; // Initialize as empty array
  try {
    console.log(`Fetching releases for artist ID: ${artistId}`);
    // Expect the paginated response
    const response = await axios.get<PaginatedArtistReleasesResponse>(
      `/releases/?artist=${artistId}`
    );
    releases.value = response.data.results; // Correctly assign the results array
  } catch (err) {
    console.error(`Failed to fetch releases for artist ${artistId}:`, err);
  } finally {
    isLoadingReleases.value = false;
  }
};

const loadData = (artistId: string) => {
  if (artistId) {
    fetchArtistDetail(artistId);
    fetchArtistReleases(artistId);
  } else {
    error.value = "Invalid Artist ID.";
    isLoadingArtist.value = false;
    isLoadingReleases.value = false;
  }
};

const onArtistUpdate = (updatedArtistData: ArtistDetail) => {
  artist.value = { ...artist.value, ...updatedArtistData };
  isEditing.value = false;
  editError.value = null;
  alert("Artist profile updated successfully!");
};

const handleUpdateError = (errorMessage: string | null) => {
  editError.value = errorMessage;
};

onMounted(() => {
  loadData(props.id);
});

watch(
  () => props.id,
  (newId) => {
    loadData(newId);
  }
);
</script>

<template>
  <div class="artist-detail-page">
    <div v-if="isLoadingArtist">Loading artist info...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <div v-else-if="artist && !isEditing" class="artist-header">
      <img
        v-if="artist.artist_picture"
        :src="artist.artist_picture"
        :alt="`${artist.name} picture`"
        class="artist-pic"
      />
      <div v-else class="artist-pic-placeholder">No Pic</div>
      <div class="artist-info">
        <h1>{{ artist.name }}</h1>
        <div class="artist-meta">
          <span v-if="artist.location"
            ><i class="fas fa-map-marker-alt"></i> {{ artist.location }}</span
          >
          <a
            v-if="artist.website_url"
            :href="artist.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            <i class="fas fa-link"></i> Website
          </a>
        </div>
        <p v-if="artist.bio" class="artist-bio">{{ artist.bio }}</p>
        <p v-else class="artist-bio">No biography available.</p>
        <button
          v-if="isOwner"
          @click="
            isEditing = true;
            editError = null;
          "
          class="edit-button"
        >
          Edit Artist Profile
        </button>
      </div>
    </div>

    <div v-else-if="artist && isEditing && isOwner">
      <h2>Edit Artist Profile</h2>
      <p v-if="editError" class="error-message">{{ editError }}</p>
      <ArtistEditForm
        :artist-id="props.id"
        :initial-data="artist"
        @artist-updated="onArtistUpdate"
        @cancel-edit="
          isEditing = false;
          editError = null;
        "
        @update-error="handleUpdateError"
      />
    </div>

    <div class="artist-releases">
      <h2>Releases by {{ artist?.name || "this artist" }}</h2>
      <div v-if="isLoadingReleases">Loading releases...</div>
      <div v-else-if="!releases || releases.length === 0">
        <!-- Added !releases check -->
        No releases found for this artist.
      </div>
      <div v-else class="releases-grid">
        <RouterLink
          v-for="release in releases"
          :key="release.id"
          :to="{ name: 'release-detail', params: { id: release.id } }"
          class="release-card"
        >
          <img
            v-if="release.cover_art"
            :src="release.cover_art"
            :alt="`${release.title} cover art`"
            class="cover-art"
          />
          <div v-else class="cover-art-placeholder">No Cover</div>
          <h3>{{ release.title }}</h3>
          <span class="release-type">{{
            release.release_type_display || release.release_type
          }}</span>
        </RouterLink>
      </div>
    </div>

    <button @click="router.back()" class="back-button">Go Back</button>
  </div>
</template>

<style scoped>
.artist-detail-page {
  max-width: 900px;
  margin: 1rem auto;
}
.artist-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2.5rem;
  align-items: center;
}
.artist-pic,
.artist-pic-placeholder {
  flex-shrink: 0;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  border: 2px solid var(--color-border);
}
.artist-info h1 {
  margin-bottom: 0.5rem;
}
.artist-meta {
  margin-bottom: 1rem;
  font-size: 0.9em;
  color: var(--color-text);
  display: flex;
  gap: 1rem;
  align-items: center;
}
.artist-meta a {
  color: var(--color-link);
  text-decoration: none;
}
.artist-meta a:hover {
  text-decoration: underline;
}
.artist-bio {
  line-height: 1.6;
}
.artist-releases {
  margin-top: 3rem;
}
.artist-releases h2 {
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}
.releases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.5rem;
}
.release-card {
  border: 1px solid var(--color-border);
  padding: 0.8rem;
  border-radius: 8px;
  text-align: center;
  background-color: var(--color-background-soft);
  transition: transform 0.2s ease-in-out;
  display: block;
  color: inherit;
  text-decoration: none;
}
.release-card:hover {
  transform: translateY(-4px);
}
.cover-art,
.cover-art-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  margin-bottom: 0.5rem;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  font-size: 0.9em;
  border-radius: 4px;
}
.release-card h3 {
  font-size: 1em;
  margin-bottom: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.release-type {
  font-size: 0.75em;
  color: var(--color-text);
  background-color: var(--color-background-mute);
  padding: 0.1em 0.4em;
  border-radius: 4px;
}
.error-message {
  color: red;
}
.back-button {
  margin-top: 2rem;
}
</style>
