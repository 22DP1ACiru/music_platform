<!-- src/views/ReleaseDetailView.vue -->
<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import axios from "axios";

// Define interfaces based on your ReleaseSerializer and nested serializers
interface ArtistInfo {
  id: number;
  name: string;
}
interface TrackInfo {
  id: number;
  title: string;
  track_number: number | null;
  duration_seconds: number | null;
  audio_file: string; // URL to the audio
}
interface ReleaseDetail extends Release {
  artist: ArtistInfo;
  tracks: TrackInfo[];
  description?: string;
  genre?: { id: number; name: string };
}
interface Release {
  // Base interface from list view (can be put in shared types file)
  id: number;
  title: string;
}

const router = useRouter(); // For potential navigation (e.g., back button)
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);

const fetchReleaseDetail = async (id: string | string[]) => {
  // Ensure id is a single string
  const releaseId = Array.isArray(id) ? id[0] : id;
  if (!releaseId) {
    error.value = "Invalid Release ID.";
    isLoading.value = false;
    return;
  }

  isLoading.value = true;
  error.value = null;
  release.value = null; // Clear previous data

  try {
    console.log(`Fetching release details for ID: ${releaseId}`);
    // Fetch data for the specific release ID
    const response = await axios.get<ReleaseDetail>(`/releases/${releaseId}/`);
    release.value = response.data;
    console.log("Fetched release:", release.value);
  } catch (err: any) {
    console.error(`Failed to fetch release ${releaseId}:`, err);
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Release not found.";
    } else {
      error.value = "Could not load release details.";
    }
  } finally {
    isLoading.value = false;
  }
};

// Fetch data when the component is mounted AND when the route ID changes
onMounted(() => {
  fetchReleaseDetail(props.id);
});

// Watch for changes in route params (if user navigates from one release detail to another)
watch(
  () => props.id,
  (newId) => {
    if (newId) {
      fetchReleaseDetail(newId);
    }
  }
);

// Helper function to format duration (optional)
const formatDuration = (seconds: number | null | undefined): string => {
  if (seconds === null || seconds === undefined) return "--:--";
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
};
</script>

<template>
  <div class="release-detail-page">
    <div v-if="isLoading">Loading release details...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="release">
      <div class="release-header">
        <img
          v-if="release.cover_art"
          :src="release.cover_art"
          :alt="`${release.title} cover art`"
          class="release-cover"
        />
        <div v-else class="release-cover-placeholder">No Cover</div>
        <div class="header-info">
          <h1>{{ release.title }}</h1>
          <h2>
            by
            <!-- Link to artist detail page later -->
            <RouterLink
              :to="{ name: 'artist-detail', params: { id: release.artist.id } }"
            >
              {{ release.artist.name }}
            </RouterLink>
          </h2>
          <p class="release-meta">
            {{ release.get_release_type_display || release.release_type }}
            <span v-if="release.genre"> • {{ release.genre.name }}</span>
            <span v-if="release.release_date">
              • Released:
              {{ new Date(release.release_date).toLocaleDateString() }}</span
            >
          </p>
          <!-- Add description if available -->
          <p v-if="release.description" class="description">
            {{ release.description }}
          </p>
        </div>
      </div>

      <div class="track-list">
        <h3>Tracklist</h3>
        <ol v-if="release.tracks && release.tracks.length > 0">
          <li
            v-for="track in release.tracks"
            :key="track.id"
            class="track-item"
          >
            <span class="track-number">{{ track.track_number }}.</span>
            <span class="track-title">{{ track.title }}</span>
            <span class="track-duration">{{
              formatDuration(track.duration_seconds)
            }}</span>
            <!-- Add Play button later -->
            <!-- <button @click="playTrack(track)">Play</button> -->
          </li>
        </ol>
        <p v-else>No tracks found for this release.</p>
      </div>

      <!-- Add Comment section later -->
    </div>
    <div v-else>
      <p>Could not load release data.</p>
    </div>
    <button @click="router.back()">Go Back</button>
    <!-- Simple back button -->
  </div>
</template>

<style scoped>
.release-detail-page {
  max-width: 900px;
  margin: 1rem auto;
}
.release-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2rem;
  align-items: flex-start; /* Align items to the top */
}
.release-cover,
.release-cover-placeholder {
  flex-shrink: 0; /* Prevent image from shrinking */
  width: 200px;
  height: 200px;
  object-fit: cover;
  background-color: var(--color-background-mute);
  border-radius: 4px;
  display: flex; /* For placeholder text */
  align-items: center; /* For placeholder text */
  justify-content: center; /* For placeholder text */
  color: var(--color-text); /* For placeholder text */
}
.header-info h1 {
  margin-bottom: 0.2rem;
  font-size: 2.5em;
}
.header-info h2 {
  margin-bottom: 0.8rem;
  font-size: 1.5em;
  font-weight: 400;
  color: var(--color-text);
}
.header-info h2 a {
  color: var(--color-heading);
  text-decoration: none;
}
.header-info h2 a:hover {
  text-decoration: underline;
}
.release-meta {
  font-size: 0.9em;
  color: var(--color-text);
  margin-bottom: 1rem;
}
.description {
  color: var(--color-text);
  line-height: 1.6;
}

.track-list {
  margin-top: 2rem;
}
.track-list h3 {
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}
.track-list ol {
  list-style: none;
  padding: 0;
}
.track-item {
  display: flex;
  align-items: center;
  padding: 0.8rem 0.5rem;
  border-bottom: 1px solid var(--color-border-hover);
  gap: 1rem;
}
.track-item:last-child {
  border-bottom: none;
}
.track-number {
  color: var(--color-text);
  min-width: 2em; /* Align numbers */
  text-align: right;
}
.track-title {
  flex-grow: 1; /* Take remaining space */
}
.track-duration {
  color: var(--color-text);
  font-size: 0.9em;
}
.error-message {
  color: red;
}
button {
  /* Style back button */
  margin-top: 2rem;
}
</style>
