<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
import axios from "axios";
import { usePlayerStore } from "@/stores/player";
import { useAuthStore } from "@/stores/auth";

interface ArtistInfo {
  id: number;
  name: string;
  user_id: number;
}
interface TrackInfo {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string;
  // Assuming TrackSerializer now returns genres_data similar to ReleaseSerializer for tracks
  genres_data?: { id: number; name: string }[];
}
interface ReleaseDetail {
  id: number;
  title: string;
  artist: ArtistInfo;
  tracks: TrackInfo[];
  cover_art: string | null;
  release_type: string;
  release_type_display: string;
  release_date: string;
  description?: string; // Made description optional if it can be null/blank
  genres_data?: { id: number; name: string }[]; // Made optional for safety
  is_published: boolean; // Added
}

const playerStore = usePlayerStore();
const authStore = useAuthStore(); // Initialize auth store
const router = useRouter();
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);

// Computed property to check if current user is the owner of the release
const isOwner = computed(() => {
  if (!authStore.isLoggedIn || !release.value || !authStore.authUser) {
    return false;
  }
  // Compare the user_id of the release's artist with the logged-in user's ID
  return release.value.artist.user_id === authStore.authUser.id;
});

const fetchReleaseDetail = async (id: string | string[]) => {
  const releaseId = Array.isArray(id) ? id[0] : id;
  if (!releaseId) {
    error.value = "Invalid Release ID.";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  error.value = null;
  release.value = null;
  try {
    const response = await axios.get<ReleaseDetail>(`/releases/${releaseId}/`);
    release.value = response.data;
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
  playerStore.playTrack({
    id: track.id,
    title: track.title,
    audio_file: track.audio_file,
    artistName: release.value?.artist?.name,
    releaseTitle: release.value?.title,
    coverArtUrl: release.value?.cover_art,
    duration: track.duration_in_seconds,
  });
};

const goToEditRelease = () => {
  if (release.value && isOwner.value) {
    router.push({ name: "release-edit", params: { id: release.value.id } });
  }
};

onMounted(() => {
  fetchReleaseDetail(props.id);
});

watch(
  () => props.id,
  (newId) => {
    if (newId) {
      fetchReleaseDetail(newId);
    }
  }
);

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
    return `${hours}:${formattedMinutes}:${formattedSeconds}`;
  } else {
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
            {{ release.release_type_display }}
            <span v-if="release.genres_data && release.genres_data.length > 0">
              • {{ release.genres_data.map((g) => g.name).join(", ") }}
            </span>
            <span v-if="release.release_date">
              • Released:
              {{ new Date(release.release_date).toLocaleDateString() }}</span
            >
            <span v-if="!release.is_published" class="draft-badge">
              (Draft)</span
            >
          </p>
          <p v-if="release.description" class="description">
            {{ release.description }}
          </p>
          <!-- Edit Button for Owner -->
          <button
            v-if="isOwner"
            @click="goToEditRelease"
            class="edit-release-button"
          >
            Edit Release
          </button>
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
            <span class="track-number">{{ track.track_number || "-" }}.</span>
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
    <button @click="router.back()" class="back-button">Go Back</button>
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
  align-items: flex-start;
}
.release-cover,
.release-cover-placeholder {
  flex-shrink: 0;
  width: 200px;
  height: 200px;
  object-fit: cover;
  background-color: var(--color-background-mute);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
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
.draft-badge {
  color: orange;
  font-weight: bold;
}
.description {
  color: var(--color-text);
  line-height: 1.6;
  margin-bottom: 1rem; /* Space before edit button */
}
.edit-release-button {
  padding: 0.5em 1em;
  font-size: 0.9em;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}
.edit-release-button:hover {
  border-color: var(--color-border-hover);
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
  min-width: 2em;
  text-align: right;
}
.track-title {
  flex-grow: 1;
}
.track-duration {
  color: var(--color-text);
  font-size: 0.9em;
}
.play-button {
  padding: 0.3em 0.8em;
  font-size: 0.9em;
  margin-left: auto;
}
.error-message {
  color: red;
}
.back-button {
  /* General style for back/action buttons */
  margin-top: 2rem;
  padding: 0.6em 1.2em;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.back-button:hover {
  border-color: var(--color-border-hover);
}
</style>
