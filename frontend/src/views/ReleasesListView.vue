<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";
import { RouterLink } from "vue-router"; // For linking to detail pages later

interface ArtistInfo {
  id: number;
  name: string;
}
interface Release {
  id: number;
  title: string;
  artist: ArtistInfo;
  cover_art: string | null;
  release_type: string;
}

const releases = ref<Release[]>([]);
const isLoading = ref(true);
const error = ref<string | null>(null);

const fetchReleases = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await axios.get<Release[]>("/releases/");
    releases.value = response.data;
  } catch (err) {
    console.error("Failed to fetch releases:", err);
    error.value = "Could not load releases.";
  } finally {
    isLoading.value = false;
  }
};

// Fetch data when the component is mounted
onMounted(fetchReleases);
</script>

<template>
  <div class="releases-list-page">
    <h2>Releases</h2>

    <div v-if="isLoading">Loading releases...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="releases.length === 0">No releases found.</div>

    <div v-else class="releases-grid">
      <div v-for="release in releases" :key="release.id" class="release-card">
        <!-- Link to detail page (add later) -->
        <!-- <RouterLink :to="{ name: 'release-detail', params: { id: release.id } }"> -->
        <img
          v-if="release.cover_art"
          :src="release.cover_art"
          :alt="`${release.title} cover art`"
          class="cover-art"
        />
        <div v-else class="cover-art-placeholder">No Cover</div>
        <h3>{{ release.title }}</h3>
        <!-- Link to artist page (add later) -->
        <!-- <RouterLink :to="{ name: 'artist-detail', params: { id: release.artist.id } }"> -->
        <p>{{ release.artist.name }}</p>
        <!-- </RouterLink> -->
        <span class="release-type">{{ release.release_type }}</span>
        <!-- </RouterLink> -->
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
.release-card {
  border: 1px solid var(--color-border);
  padding: 1rem;
  border-radius: 8px;
  text-align: center;
  background-color: var(--color-background-soft);
  transition: transform 0.2s ease-in-out;
}
.release-card:hover {
  transform: translateY(-5px);
}
.release-card a {
  /* Style links if wrapping card */
  text-decoration: none;
  color: inherit;
}
.cover-art {
  width: 100%;
  aspect-ratio: 1 / 1; /* Make cover art square */
  object-fit: cover;
  margin-bottom: 0.8rem;
  background-color: var(--color-background-mute); /* BG for images that fail */
}
.cover-art-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  margin-bottom: 0.8rem;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  font-size: 0.9em;
}
.release-card h3 {
  font-size: 1.1em;
  margin-bottom: 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.release-card p {
  font-size: 0.95em;
  margin-bottom: 0.5rem;
  color: var(--color-text);
}
.release-type {
  font-size: 0.8em;
  color: var(--color-text);
  background-color: var(--color-background-mute);
  padding: 0.1em 0.4em;
  border-radius: 4px;
}
.error-message {
  color: red;
}
</style>
