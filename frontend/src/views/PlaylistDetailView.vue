<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import {
  usePlaylistStore,
  type UpdatePlaylistPayload,
} from "@/stores/playlistStore";
import { useAuthStore } from "@/stores/auth";
import { usePlayerStore } from "@/stores/player";
import type { TrackInfoFromApi, PlayerTrackInfo, Playlist } from "@/types"; // Added Playlist to import

const route = useRoute();
const router = useRouter();
const playlistStore = usePlaylistStore();
const authStore = useAuthStore();
const playerStore = usePlayerStore();

const playlist = computed(() => playlistStore.currentPlaylistDetail);
const isLoading = computed(() => playlistStore.isLoadingPlaylistDetail);
const error = computed(() => playlistStore.detailError);

const isEditingMeta = ref(false);
const editTitle = ref("");
const editDescription = ref("");
const editIsPublic = ref(true);

const trackIdToAdd = ref<number | null>(null);

const isOwner = computed(() => {
  return (
    authStore.isLoggedIn &&
    playlist.value &&
    playlist.value.owner === authStore.authUser?.username
  );
});

const fetchPlaylist = async () => {
  const playlistId = route.params.id as string;
  if (playlistId) {
    await playlistStore.fetchPlaylistDetail(playlistId);
    if (playlist.value) {
      editTitle.value = playlist.value.title;
      editDescription.value = playlist.value.description || "";
      editIsPublic.value = playlist.value.is_public;
    }
  }
};

onMounted(fetchPlaylist);

watch(
  () => route.params.id,
  (newId) => {
    if (newId) fetchPlaylist();
  }
);

const handleSaveMetadata = async () => {
  if (!playlist.value) return;
  const payload: UpdatePlaylistPayload = {
    title: editTitle.value,
    description: editDescription.value,
    is_public: editIsPublic.value,
  };
  const success = await playlistStore.updatePlaylist(
    playlist.value.id,
    payload
  );
  if (success) {
    isEditingMeta.value = false;
  }
};

const handleDeletePlaylist = async () => {
  if (
    playlist.value &&
    confirm(
      `Are you sure you want to delete the playlist "${playlist.value.title}"? This cannot be undone.`
    )
  ) {
    const success = await playlistStore.deletePlaylist(playlist.value.id);
    if (success) {
      router.push({ name: "my-playlists" });
    }
  }
};

const handleAddTrack = async () => {
  if (!playlist.value || trackIdToAdd.value === null) return;
  const success = await playlistStore.addTrackToPlaylist(
    playlist.value.id,
    trackIdToAdd.value
  );
  if (success) {
    trackIdToAdd.value = null;
  }
};

const handleRemoveTrack = async (trackId: number) => {
  if (playlist.value && confirm("Remove this track from the playlist?")) {
    await playlistStore.removeTrackFromPlaylist(playlist.value.id, trackId);
  }
};

// Updated mapToPlayerTrack function
const mapToPlayerTrack = (
  apiTrack: TrackInfoFromApi,
  playlistData: Playlist
): PlayerTrackInfo => {
  return {
    id: apiTrack.id,
    title: apiTrack.title,
    audio_file: apiTrack.stream_url,
    // Use track-specific details first, then fall back to playlist-level (release) details
    artistName: apiTrack.artist_name || playlistData.artist?.name, // Assuming Playlist type might have artist for context
    releaseTitle: apiTrack.release_title || playlistData.title, // Use playlist title as fallback for release title
    coverArtUrl: apiTrack.release_cover_art || playlistData.cover_art, // Use track's release cover, then playlist cover
    duration: apiTrack.duration_in_seconds,
  };
};

const playTrackFromPlaylist = (track: TrackInfoFromApi) => {
  if (!playlist.value || !playlist.value.tracks) return;

  const allPlaylistTracksForPlayer: PlayerTrackInfo[] =
    playlist.value.tracks.map((apiTrack) =>
      mapToPlayerTrack(apiTrack, playlist.value!)
    );

  const clickedTrackIndex = allPlaylistTracksForPlayer.findIndex(
    (pt) => pt.id === track.id
  );

  if (clickedTrackIndex !== -1) {
    playerStore.setQueueAndPlay(allPlaylistTracksForPlayer, clickedTrackIndex);
  } else {
    playerStore.playTrack(mapToPlayerTrack(track, playlist.value!));
  }
};

const playAllFromPlaylist = () => {
  if (
    !playlist.value ||
    !playlist.value.tracks ||
    playlist.value.tracks.length === 0
  )
    return;
  const allPlaylistTracksForPlayer: PlayerTrackInfo[] =
    playlist.value.tracks.map((apiTrack) =>
      mapToPlayerTrack(apiTrack, playlist.value!)
    );
  playerStore.setQueueAndPlay(allPlaylistTracksForPlayer, 0);
};

const addTrackToPlayerQueue = (track: TrackInfoFromApi) => {
  if (!playlist.value) return;
  playerStore.addTrackToQueue(mapToPlayerTrack(track, playlist.value));
};

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
  <div class="playlist-detail-view">
    <div v-if="isLoading" class="loading-message">Loading playlist...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="playlist" class="playlist-content">
      <div class="playlist-header">
        <div class="cover-art-container">
          <img
            v-if="playlist.cover_art"
            :src="playlist.cover_art"
            alt="Playlist cover"
            class="playlist-cover-art"
          />
          <div v-else class="playlist-cover-art-placeholder">🎵</div>
        </div>
        <div class="playlist-info">
          <template v-if="!isEditingMeta">
            <h1>{{ playlist.title }}</h1>
            <p v-if="playlist.description" class="playlist-description">
              {{ playlist.description }}
            </p>
            <p class="playlist-meta">
              By {{ playlist.owner }} • {{ playlist.track_count }} track{{
                playlist.track_count !== 1 ? "s" : ""
              }}
              <span v-if="!playlist.is_public" class="private-badge"
                >Private</span
              >
            </p>
          </template>
          <form
            v-else
            @submit.prevent="handleSaveMetadata"
            class="edit-meta-form"
          >
            <div class="form-group">
              <label for="edit-title">Title:</label>
              <input type="text" id="edit-title" v-model="editTitle" required />
            </div>
            <div class="form-group">
              <label for="edit-description">Description:</label>
              <textarea
                id="edit-description"
                v-model="editDescription"
                rows="3"
              ></textarea>
            </div>
            <div class="form-group form-group-checkbox">
              <input type="checkbox" id="edit-public" v-model="editIsPublic" />
              <label for="edit-public">Public</label>
            </div>
            <div class="edit-form-actions">
              <button type="submit">Save</button>
              <button type="button" @click="isEditingMeta = false">
                Cancel
              </button>
            </div>
          </form>
          <div class="playlist-actions">
            <button
              @click="playAllFromPlaylist"
              class="action-button play-all-btn"
              v-if="playlist.tracks && playlist.tracks.length > 0"
            >
              ▶ Play All
            </button>
            <button
              v-if="isOwner && !isEditingMeta"
              @click="isEditingMeta = true"
              class="action-button"
            >
              Edit Details
            </button>
            <button
              v-if="isOwner"
              @click="handleDeletePlaylist"
              class="action-button delete-btn"
            >
              Delete Playlist
            </button>
          </div>
        </div>
      </div>

      <div v-if="isOwner" class="add-track-section">
        <h4>Add Track to Playlist</h4>
        <form @submit.prevent="handleAddTrack" class="add-track-form">
          <input
            type="number"
            v-model.number="trackIdToAdd"
            placeholder="Enter Track ID"
          />
          <button type="submit">Add Track</button>
        </form>
        <p class="info-text">
          You can find Track IDs on release pages or by inspecting network
          requests (for now).
        </p>
      </div>

      <div class="tracks-list-section">
        <h3>Tracks</h3>
        <ul
          v-if="playlist.tracks && playlist.tracks.length > 0"
          class="tracks-list"
        >
          <li
            v-for="(track, index) in playlist.tracks"
            :key="track.id"
            class="track-item"
            :class="{
              'is-playing':
                playerStore.currentTrack?.id === track.id &&
                playerStore.isPlaying,
              'is-paused':
                playerStore.currentTrack?.id === track.id &&
                !playerStore.isPlaying &&
                playerStore.currentTrack?.id === track.id,
            }"
          >
            <span class="track-item-number">{{ index + 1 }}.</span>
            <button
              @click="playTrackFromPlaylist(track)"
              class="play-icon-button"
              :title="
                playerStore.currentTrack?.id === track.id &&
                playerStore.isPlaying
                  ? 'Pause'
                  : 'Play Track'
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
            <div class="track-item-info">
              <span class="track-item-title">{{ track.title }}</span>
              <!-- Display artist_name from track if available -->
              <span class="track-item-artist" v-if="track.artist_name">
                <!-- Link to artist if artist_id is available on track -->
                <RouterLink
                  v-if="track.artist_id"
                  :to="{
                    name: 'artist-detail',
                    params: { id: track.artist_id },
                  }"
                  >{{ track.artist_name }}</RouterLink
                >
                <span v-else>{{ track.artist_name }}</span>
              </span>
            </div>
            <span class="track-item-duration">{{
              formatDuration(track.duration_in_seconds)
            }}</span>
            <div class="track-item-actions">
              <button
                @click="addTrackToPlayerQueue(track)"
                class="action-button-small add-queue-btn"
                title="Add to Queue"
              >
                +
              </button>
              <button
                v-if="isOwner"
                @click="handleRemoveTrack(track.id)"
                class="action-button-small remove-track-btn"
                title="Remove Track"
              >
                ×
              </button>
            </div>
          </li>
        </ul>
        <p v-else class="empty-state">This playlist is empty.</p>
      </div>
    </div>
    <div v-else class="empty-state">
      Playlist not found or could not be loaded.
    </div>
  </div>
</template>

<style scoped>
.playlist-detail-view {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1rem;
}
.loading-message,
.empty-state {
  text-align: center;
  padding: 2rem;
  font-style: italic;
  color: var(--color-text-light);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.playlist-content {
  background-color: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.playlist-header {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  align-items: flex-start;
}
.cover-art-container {
  flex-shrink: 0;
}
.playlist-cover-art,
.playlist-cover-art-placeholder {
  width: 180px;
  height: 180px;
  object-fit: cover;
  border-radius: 6px;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 3rem;
  color: var(--color-text-light);
}
.playlist-info {
  flex-grow: 1;
}
.playlist-info h1 {
  font-size: 2em;
  margin: 0 0 0.5rem 0;
  color: var(--color-heading);
}
.playlist-description {
  font-size: 0.95em;
  color: var(--color-text);
  margin-bottom: 0.5rem;
  white-space: pre-wrap;
}
.playlist-meta {
  font-size: 0.9em;
  color: var(--color-text-light);
  margin-bottom: 1rem;
}
.private-badge {
  margin-left: 0.5em;
  background-color: var(--color-background-mute);
  padding: 0.1em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}

.edit-meta-form .form-group {
  margin-bottom: 0.8rem;
}
.edit-meta-form label {
  display: block;
  font-size: 0.9em;
  margin-bottom: 0.2rem;
}
.edit-meta-form input[type="text"],
.edit-meta-form textarea {
  width: 100%;
  padding: 0.5em;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.95em;
}
.edit-meta-form textarea {
  min-height: 60px;
}
.form-group-checkbox {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.9em;
}
.form-group-checkbox input {
  width: auto;
}
.edit-form-actions {
  margin-top: 0.8rem;
  display: flex;
  gap: 0.5rem;
}
.edit-form-actions button {
  font-size: 0.9em;
  padding: 0.4em 0.8em;
}

.playlist-actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.action-button {
  padding: 0.6em 1em;
  font-size: 0.9em;
  border-radius: 4px;
  cursor: pointer;
}
.play-all-btn {
  background-color: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
}
.delete-btn {
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
  border: 1px solid var(--vt-c-red-dark);
}

.add-track-section {
  margin: 2rem 0;
  padding: 1rem;
  background-color: var(--color-background-mute);
  border-radius: 6px;
}
.add-track-section h4 {
  margin-top: 0;
}
.add-track-form {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}
.add-track-form input {
  flex-grow: 1;
  padding: 0.5em;
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.add-track-form button {
  padding: 0.5em 0.8em;
}
.info-text {
  font-size: 0.8em;
  color: var(--color-text-light);
  margin-top: 0.5rem;
}

.tracks-list-section h3 {
  margin-bottom: 1rem;
  font-size: 1.3em;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}
.tracks-list {
  list-style: none;
  padding: 0;
}
.track-item {
  display: flex;
  align-items: center;
  padding: 0.7rem 0.3rem;
  border-bottom: 1px solid var(--color-border-hover);
  gap: 0.8rem;
  transition: background-color 0.1s ease;
}
.track-item:last-child {
  border-bottom: none;
}
.track-item:hover {
  background-color: var(--color-background-mute);
}
.track-item.is-playing,
.track-item.is-paused {
  background-color: var(--color-accent-soft);
}
.track-item.is-playing .track-item-title,
.track-item.is-paused .track-item-title {
  color: var(--color-accent);
  font-weight: 600;
}

.track-item-number {
  font-size: 0.9em;
  color: var(--color-text-light);
  min-width: 1.8em;
  text-align: right;
}
.play-icon-button {
  background: none;
  border: none;
  font-size: 1.1em;
  cursor: pointer;
  color: var(--color-accent);
  padding: 0 0.3em;
}
.track-item-info {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.track-item-title {
  font-size: 1em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-item-artist {
  font-size: 0.85em;
  color: var(--color-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-item-artist a {
  color: var(--color-text-light);
  text-decoration: none;
}
.track-item-artist a:hover {
  text-decoration: underline;
  color: var(--color-link);
}
.track-item-duration {
  font-size: 0.9em;
  color: var(--color-text-light);
}
.track-item-actions {
  display: flex;
  gap: 0.3rem;
}
.action-button-small {
  font-size: 0.85em;
  padding: 0.2em 0.5em;
  min-width: 24px;
  text-align: center;
}
.remove-track-btn {
  color: var(--vt-c-red);
}
</style>
