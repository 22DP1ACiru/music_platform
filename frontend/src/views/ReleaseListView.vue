// frontend/src/views/ReleaseListView.vue
<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";
import { RouterLink } from "vue-router";

interface ArtistInfo {
  id: number;
  name: string;
}

// This interface should match the structure of individual items in the "results" array
interface Release {
  id: number;
  title: string;
  artist: ArtistInfo | null; // Allow artist to be null as per previous fix
  cover_art: string | null;
  release_type: string;
  release_type_display?: string;
}

// This interface matches the paginated response from DRF
interface PaginatedReleasesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: Release[];
}

const releases = ref<Release[]>([]);
const isLoading = ref(true);
const error = ref<string | null>(null);

const fetchReleases = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    // Expect the paginated response structure
    const response = await axios.get<PaginatedReleasesResponse>("/releases/");
    releases.value = response.data.results; // Assign the 'results' array
  } catch (err) {
    console.error("Failed to fetch releases:", err);
    error.value = "Could not load releases.";
  } finally {
    isLoading.value = false;
  }
};

onMounted(fetchReleases);
</script>

<template>
  <div class="releases-list-page">
    <h2>Releases</h2>

    <div v-if="isLoading">Loading releases...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!releases || releases.length === 0">No releases found.</div>
    <!-- Added !releases check -->

    <div v-else class="releases-grid">
      <div
        v-for="release in releases"
        :key="release.id"
        class="release-card-wrapper"
      >
        <RouterLink
          :to="{ name: 'release-detail', params: { id: release.id } }"
          class="release-card-main-link"
        >
          <img
            v-if="release.cover_art"
            :src="release.cover_art"
            :alt="`${release.title} cover art`"
            class="cover-art"
          />
          <div v-else class="cover-art-placeholder">No Cover</div>
          <h3>{{ release.title }}</h3>
        </RouterLink>
        <RouterLink
          v-if="release.artist"
          :to="{ name: 'artist-detail', params: { id: release.artist.id } }"
          class="artist-link"
        >
          <p>{{ release.artist.name }}</p>
        </RouterLink>
        <p v-else class="artist-link">
          <em>Unknown Artist</em>
        </p>
        <span class="release-type">{{
          release.release_type_display || release.release_type
        }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.releases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1.5rem;
  margin-top: 1rem;
}
.release-card-wrapper {
  border: 1px solid var(--color-border);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  background-color: var(--color-background-soft);
  transition: transform 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
}
.release-card-wrapper:hover {
  transform: translateY(-5px);
}
.release-card-main-link {
  text-decoration: none;
  color: inherit;
  display: block;
  margin-bottom: 0.5rem;
}
.cover-art,
.cover-art-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  margin-bottom: 0.8rem;
  background-color: var(--color-background-mute);
  border-radius: 4px;
}
.cover-art-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  font-size: 0.9em;
}
.release-card-wrapper h3 {
  font-size: 1.1em;
  margin-bottom: 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-heading);
}
.artist-link {
  text-decoration: none;
}
.artist-link p {
  font-size: 0.95em;
  margin-bottom: 0.5rem;
  color: var(--color-text-light);
  text-decoration: none;
}
.artist-link:hover p {
  color: var(--color-link-hover);
  text-decoration: underline;
}
.release-type {
  font-size: 0.8em;
  color: var(--color-text);
  background-color: var(--color-background-mute);
  padding: 0.1em 0.4em;
  border-radius: 4px;
  align-self: center;
  margin-top: auto;
}
.error-message {
  color: red;
}
</style>
