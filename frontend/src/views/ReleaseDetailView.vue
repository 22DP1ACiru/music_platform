<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
import axios from "axios";
import { usePlayerStore, type PlayerTrackInfo } from "@/stores/player"; // Import PlayerTrackInfo
import { useAuthStore } from "@/stores/auth";

interface ArtistInfo {
  id: number;
  name: string;
  user_id: number; // Added to check ownership
}

// Updated TrackInfoFromApi to include stream_url and ensure audio_file is the original
interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string; // Original direct media URL (e.g., for download link if needed)
  stream_url: string; // URL for the streaming endpoint
  genres_data?: { id: number; name: string }[];
}

interface ReleaseDetail {
  id: number;
  title: string;
  artist: ArtistInfo;
  tracks: TrackInfoFromApi[];
  cover_art: string | null;
  release_type: string;
  release_type_display: string;
  release_date: string;
  description?: string;
  genres_data?: { id: number; name: string }[];
  is_published: boolean;
}

const playerStore = usePlayerStore();
const authStore = useAuthStore();
const router = useRouter();
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);

const isOwner = computed(() => {
  if (!authStore.isLoggedIn || !release.value || !authStore.authUser) {
    return false;
  }
  // Ensure artist and user_id exist before comparison
  return (
    release.value.artist &&
    release.value.artist.user_id === authStore.authUser.id
  );
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
  release.value = null; // Clear previous release data
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

// Helper to convert API track to PlayerTrackInfo
function mapToPlayerTrackInfo(
  apiTrack: TrackInfoFromApi,
  releaseData: ReleaseDetail
): PlayerTrackInfo {
  return {
    id: apiTrack.id,
    title: apiTrack.title,
    audio_file: apiTrack.stream_url, // IMPORTANT: Use stream_url for playback
    artistName: releaseData.artist?.name,
    releaseTitle: releaseData.title,
    coverArtUrl: releaseData.cover_art,
    duration: apiTrack.duration_in_seconds,
  };
}

const handlePlayTrack = (clickedTrack: TrackInfoFromApi) => {
  if (!release.value || !release.value.tracks) return;

  const allReleasePlayerTracks: PlayerTrackInfo[] = release.value.tracks.map(
    (apiTrack) => mapToPlayerTrackInfo(apiTrack, release.value!)
  );

  const clickedTrackIndex = allReleasePlayerTracks.findIndex(
    (pt) => pt.id === clickedTrack.id
  );

  if (clickedTrackIndex !== -1) {
    playerStore.setQueueAndPlay(allReleasePlayerTracks, clickedTrackIndex);
  } else {
    console.error("Clicked track not found in mapped release tracks.");
    playerStore.playTrack(mapToPlayerTrackInfo(clickedTrack, release.value!));
  }
};

const handlePlayAllFromRelease = () => {
  if (
    !release.value ||
    !release.value.tracks ||
    release.value.tracks.length === 0
  )
    return;

  const allReleasePlayerTracks: PlayerTrackInfo[] = release.value.tracks.map(
    (apiTrack) => mapToPlayerTrackInfo(apiTrack, release.value!)
  );
  playerStore.setQueueAndPlay(allReleasePlayerTracks, 0);
};

const handleAddTrackToQueue = (trackToAdd: TrackInfoFromApi) => {
  if (!release.value) return;
  playerStore.addTrackToQueue(mapToPlayerTrackInfo(trackToAdd, release.value));
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
  if (
    totalSeconds === null ||
    totalSeconds === undefined ||
    totalSeconds < 0 ||
    !isFinite(totalSeconds)
  ) {
    return "--:--";
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
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
          <div class="header-actions">
            <button
              @click="handlePlayAllFromRelease"
              class="play-all-button"
              v-if="release.tracks && release.tracks.length > 0"
            >
              Play All
            </button>
            <button
              v-if="isOwner"
              @click="goToEditRelease"
              class="edit-release-button"
            >
              Edit Release
            </button>
          </div>
        </div>
      </div>

      <div class="track-list">
        <h3>Tracklist</h3>
        <ol v-if="release.tracks && release.tracks.length > 0">
          <li
            v-for="track in release.tracks"
            :key="track.id"
            class="track-item"
            :class="{
              'is-playing':
                playerStore.currentTrack?.id === track.id &&
                playerStore.isPlaying,
              'is-paused':
                playerStore.currentTrack?.id === track.id &&
                !playerStore.isPlaying &&
                playerStore.currentTrack?.id === track.id, // Condition for paused but current
            }"
          >
            <button
              @click="handlePlayTrack(track)"
              class="play-icon-button"
              :title="
                playerStore.currentTrack?.id === track.id &&
                playerStore.isPlaying
                  ? 'Pause'
                  : 'Play'
              "
            >
              <span
                v-if="
                  playerStore.currentTrack?.id === track.id &&
                  playerStore.isPlaying
                "
                class="pause-icon"
                >❚❚</span
              >
              <span v-else class="play-icon">►</span>
            </button>
            <span class="track-number">{{ track.track_number || "-" }}.</span>
            <span class="track-title">{{ track.title }}</span>
            <span class="track-duration">{{
              formatDuration(track.duration_in_seconds)
            }}</span>
            <button
              @click="handleAddTrackToQueue(track)"
              class="add-queue-button"
              title="Add to Queue"
            >
              +
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
  margin-bottom: 1rem;
}
.header-actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.75rem;
}
.play-all-button,
.edit-release-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  background-color: var(--color-accent, #007bff);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.play-all-button:hover {
  background-color: var(--color-accent-hover, #0056b3);
}
.edit-release-button {
  background-color: var(--color-background-soft);
  color: var(--color-text);
  border: 1px solid var(--color-border);
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
  transition: background-color 0.2s ease;
}
.track-item:hover {
  background-color: var(--color-background-soft);
}
.track-item.is-playing,
.track-item.is-paused {
  background-color: var(--color-background-mute);
}
.track-item.is-playing .track-title,
.track-item.is-paused .track-title {
  color: var(--color-accent); /* Highlight title of current track */
  font-weight: 600;
}

.play-icon-button {
  background: none;
  border: none;
  color: var(--color-accent, #007bff);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.2em 0.4em;
  width: 28px; /* Fixed width for alignment */
  text-align: center;
}
.play-icon-button:hover {
  color: var(--color-accent-hover, #0056b3);
}
.play-icon,
.pause-icon {
  display: inline-block;
}

.track-item:last-child {
  border-bottom: none;
}
.track-number {
  color: var(--color-text-light);
  min-width: 2em;
  text-align: right;
}
.track-title {
  flex-grow: 1;
}
.track-duration {
  color: var(--color-text-light);
  font-size: 0.9em;
}
.add-queue-button {
  padding: 0.3em 0.7em;
  font-size: 1em; /* Make it a bit bigger for easier clicking */
  line-height: 1;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 50%; /* Make it round */
  color: var(--color-text);
  margin-left: 0.5rem; /* Spacing from duration */
  cursor: pointer;
  min-width: 28px; /* Consistent size */
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.add-queue-button:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.error-message {
  color: red;
}
.back-button {
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
