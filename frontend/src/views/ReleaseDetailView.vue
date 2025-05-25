<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import axios from "axios";
import { usePlayerStore } from "@/stores/player";

// Define interfaces based on your ReleaseSerializer and nested serializers
interface ArtistInfo {
  id: number;
  name: string;
  user_id: number; // Assuming ArtistSerializer now includes user_id
}
interface TrackInfo {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string; // URL to the audio
}
interface ReleaseDetail {
  id: number;
  title: string;
  artist: ArtistInfo;
  tracks: TrackInfo[];
  cover_art: string | null; // Added for consistency with header
  release_type: string; // Raw type
  release_type_display: string; // Display type from serializer
  release_date: string; // ISO date string
  description?: string;
  genre?: { id: number; name: string };
}

const playerStore = usePlayerStore();
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

const handlePlayTrack = (track: TrackInfo) => {
  // Construct the object expected by the player store's playTrack action
  playerStore.playTrack({
    id: track.id,
    title: track.title,
    audio_file: track.audio_file,
    artistName: release.value?.artist?.name, // Get artist name from release data
    // Add cover art etc. later if needed
  });
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
const formatDuration = (totalSeconds: number | null | undefined): string => {
  if (totalSeconds === null || totalSeconds === undefined || totalSeconds < 0) {
    return "--:--";
  }

  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const formattedSeconds = seconds.toString().padStart(2, "0");
  const formattedMinutes = minutes.toString().padStart(2, "0");

  if (hours > 0) {
    // Include hours if duration is an hour or more
    return `${hours}:${formattedMinutes}:${formattedSeconds}`;
  } else {
    // Only show minutes and seconds if less than an hour
    return `${minutes}:${formattedSeconds}`;
  }
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
            <RouterLink
              :to="{ name: 'artist-detail', params: { id: release.artist.id } }"
            >
              {{ release.artist.name }}
            </RouterLink>
          </h2>
          <p class="release-meta">
            {{ release.release_type_display }} <!-- Use the display name -->
            <span v-if="release.genre"> • {{ release.genre.name }}</span>
            <span v-if="release.release_date">
              • Released:
              {{ new Date(release.release_date).toLocaleDateString() }}</span
            >
          </p>
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
              formatDuration(track.duration_in_seconds)
            }}</span>
            <button @click="handlePlayTrack(track)" class="play-button">
              Play
            </button>
          </li>
        </ol>
        <p v-else>No tracks found for this release.</p>
      </div>

    </div>
    <div v-else>
      <p>Could not load release data.</p>
    </div>
    <button @click="router.back()">Go Back</button>
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
.play-button {
  /* Add styling for your play button */
  padding: 0.3em 0.8em;
  font-size: 0.9em;
  margin-left: auto; /* Pushes button to the right */
}
.error-message {
  color: red;
}
button {
  /* Style back button */
  margin-top: 2rem;
}
</style>