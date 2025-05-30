<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { useRoute, RouterLink } from "vue-router";
import axios from "axios";
import type { ArtistInfo, ReleaseSummary } from "@/types";
import ReleaseCardSmall from "@/components/release/ReleaseCardSmall.vue"; // Re-use for consistency

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

const route = useRoute();
const searchQuery = ref((route.query.q as string) || "");

const artistResults = ref<ArtistInfo[]>([]);
const releaseResults = ref<ReleaseSummary[]>([]);

const isLoadingArtists = ref(false);
const isLoadingReleases = ref(false);
const errorArtists = ref<string | null>(null);
const errorReleases = ref<string | null>(null);

const performSearch = async (query: string) => {
  if (!query) {
    artistResults.value = [];
    releaseResults.value = [];
    return;
  }

  // Search Artists
  isLoadingArtists.value = true;
  errorArtists.value = null;
  try {
    const response = await axios.get<PaginatedResponse<ArtistInfo>>(
      `/artists/?search=${encodeURIComponent(query)}`
    );
    artistResults.value = response.data.results;
  } catch (err) {
    console.error("Search artists error:", err);
    errorArtists.value = "Could not load artist search results.";
  } finally {
    isLoadingArtists.value = false;
  }

  // Search Releases
  isLoadingReleases.value = true;
  errorReleases.value = null;
  try {
    const response = await axios.get<PaginatedResponse<ReleaseSummary>>(
      `/releases/?search=${encodeURIComponent(query)}`
    );
    releaseResults.value = response.data.results;
  } catch (err) {
    console.error("Search releases error:", err);
    errorReleases.value = "Could not load release search results.";
  } finally {
    isLoadingReleases.value = false;
  }
};

// Watch for changes in the route query 'q' to re-trigger search
watch(
  () => route.query.q,
  (newQuery) => {
    const queryStr = Array.isArray(newQuery) ? newQuery[0] : newQuery;
    searchQuery.value = queryStr || "";
    performSearch(searchQuery.value);
  },
  { immediate: true } // Perform search immediately when component loads with a query
);

// Also perform search on mount if query is already there (e.g. direct navigation)
onMounted(() => {
  if (searchQuery.value) {
    performSearch(searchQuery.value);
  }
});
</script>

<template>
  <div class="search-view">
    <h1>Search Results for "{{ searchQuery }}"</h1>

    <div class="search-results-container">
      <!-- Artists Section -->
      <section class="results-section">
        <h2>Artists</h2>
        <div v-if="isLoadingArtists" class="loading-message">
          Searching artists...
        </div>
        <div v-else-if="errorArtists" class="error-message">
          {{ errorArtists }}
        </div>
        <div v-else-if="artistResults.length === 0" class="no-results-message">
          No artists found matching your query.
        </div>
        <ul v-else class="artist-results-list">
          <li
            v-for="artist in artistResults"
            :key="artist.id"
            class="artist-result-item"
          >
            <RouterLink
              :to="{ name: 'artist-detail', params: { id: artist.id } }"
            >
              <img
                v-if="artist.artist_picture"
                :src="artist.artist_picture"
                :alt="artist.name"
                class="artist-thumbnail"
              />
              <div v-else class="artist-thumbnail-placeholder">👤</div>
              <span class="artist-name">{{ artist.name }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Releases Section -->
      <section class="results-section">
        <h2>Releases</h2>
        <div v-if="isLoadingReleases" class="loading-message">
          Searching releases...
        </div>
        <div v-else-if="errorReleases" class="error-message">
          {{ errorReleases }}
        </div>
        <div v-else-if="releaseResults.length === 0" class="no-results-message">
          No releases found matching your query.
        </div>
        <div v-else class="releases-grid">
          <ReleaseCardSmall
            v-for="release in releaseResults"
            :key="release.id"
            :release="release"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.search-view {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 1rem;
}
.search-view h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--color-heading);
  word-break: break-all; /* Ensure long search queries wrap */
}

.search-results-container {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.results-section h2 {
  font-size: 1.6em;
  color: var(--color-heading);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border);
}

.loading-message,
.no-results-message {
  text-align: center;
  padding: 1.5rem;
  font-style: italic;
  color: var(--color-text-light);
  background-color: var(--color-background-soft);
  border-radius: 6px;
}

.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  text-align: center;
}

/* Artist Results Styling */
.artist-results-list {
  list-style: none;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}
.artist-result-item a {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  text-decoration: none;
  color: var(--color-text);
  transition: background-color 0.2s ease;
}
.artist-result-item a:hover {
  background-color: var(--color-background-mute);
  border-color: var(--color-border-hover);
}
.artist-thumbnail,
.artist-thumbnail-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  margin-right: 0.75rem;
  flex-shrink: 0;
  background-color: var(--color-background-mute);
}
.artist-thumbnail-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}
.artist-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Releases Grid (reusing existing grid style concept) */
.releases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1.5rem;
}
</style>
