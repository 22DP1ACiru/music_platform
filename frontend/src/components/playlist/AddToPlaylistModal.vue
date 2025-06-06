<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { usePlaylistStore } from "@/stores/playlist";
import type { Playlist, TrackInfoFromApi } from "@/types";
import axios from "axios"; // For direct API call if store pagination is complex

const props = defineProps<{
  isVisible: boolean;
  trackToAdd: TrackInfoFromApi | null;
}>();

const emit = defineEmits(["close", "trackAdded"]);

const playlistStore = usePlaylistStore();

const userPlaylists = ref<Playlist[]>([]);
const isLoadingPlaylists = ref(false);
const errorLoadingPlaylists = ref<string | null>(null);
const successMessage = ref<string | null>(null);
const addingToPlaylistId = ref<number | null>(null);

// Pagination (basic client-side example, can be enhanced with server-side)
const currentPage = ref(1);
const itemsPerPage = 5;
const totalPages = computed(() =>
  Math.ceil(userPlaylists.value.length / itemsPerPage)
);
const paginatedPlaylists = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  const end = start + itemsPerPage;
  return userPlaylists.value.slice(start, end);
});

async function fetchUserPlaylists() {
  isLoadingPlaylists.value = true;
  errorLoadingPlaylists.value = null;
  try {
    // Using the existing store action which fetches all user's playlists
    await playlistStore.fetchMyPlaylists();
    userPlaylists.value = playlistStore.myPlaylists;
  } catch (err) {
    console.error("AddToPlaylistModal: Failed to fetch user playlists:", err);
    errorLoadingPlaylists.value = "Could not load your playlists.";
  } finally {
    isLoadingPlaylists.value = false;
  }
}

async function addTrackToSelectedPlaylist(playlistId: number) {
  if (!props.trackToAdd) return;
  addingToPlaylistId.value = playlistId;
  successMessage.value = null;
  errorLoadingPlaylists.value = null; // Clear general error

  const success = await playlistStore.addTrackToPlaylist(
    playlistId,
    props.trackToAdd.id
  );

  addingToPlaylistId.value = null;
  if (success) {
    successMessage.value = `Track "${props.trackToAdd.title}" added successfully!`;
    emit("trackAdded"); // Notify parent
    setTimeout(() => {
      // Auto-close after a short delay
      emit("close");
      successMessage.value = null;
    }, 1500);
  } else {
    errorLoadingPlaylists.value =
      playlistStore.detailError || "Failed to add track to playlist.";
  }
}

watch(
  () => props.isVisible,
  (newVal) => {
    if (newVal) {
      successMessage.value = null; // Clear messages when modal opens
      errorLoadingPlaylists.value = null;
      currentPage.value = 1; // Reset pagination
      if (playlistStore.myPlaylists.length === 0) {
        // Fetch only if not already loaded
        fetchUserPlaylists();
      } else {
        userPlaylists.value = playlistStore.myPlaylists; // Use already fetched playlists
      }
    }
  }
);

onMounted(() => {
  if (props.isVisible) {
    fetchUserPlaylists();
  }
});

const changePage = (newPage: number) => {
  if (newPage >= 1 && newPage <= totalPages.value) {
    currentPage.value = newPage;
  }
};
</script>

<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h4>Add "{{ trackToAdd?.title || "Track" }}" to Playlist</h4>
        <button @click="$emit('close')" class="close-btn">&times;</button>
      </div>
      <div class="modal-body">
        <div v-if="isLoadingPlaylists" class="loading-message">
          Loading playlists...
        </div>
        <div v-else-if="errorLoadingPlaylists" class="error-message">
          {{ errorLoadingPlaylists }}
        </div>
        <div v-else-if="userPlaylists.length === 0" class="empty-message">
          You don't have any playlists.
          <RouterLink :to="{ name: 'playlist-create' }" @click="$emit('close')"
            >Create one first!</RouterLink
          >
        </div>
        <ul v-else class="playlist-selection-list">
          <li
            v-for="playlist in paginatedPlaylists"
            :key="playlist.id"
            class="playlist-item"
          >
            <img
              v-if="playlist.cover_art"
              :src="playlist.cover_art"
              alt="Cover"
              class="playlist-cover-small"
            />
            <div v-else class="playlist-cover-small placeholder">🎵</div>
            <span class="playlist-title">{{ playlist.title }}</span>
            <button
              @click="addTrackToSelectedPlaylist(playlist.id)"
              :disabled="addingToPlaylistId === playlist.id"
              class="add-button"
            >
              {{ addingToPlaylistId === playlist.id ? "Adding..." : "Add" }}
            </button>
          </li>
        </ul>

        <div v-if="totalPages > 1" class="pagination-controls">
          <button
            @click="changePage(currentPage - 1)"
            :disabled="currentPage <= 1"
          >
            Prev
          </button>
          <span>Page {{ currentPage }} of {{ totalPages }}</span>
          <button
            @click="changePage(currentPage + 1)"
            :disabled="currentPage >= totalPages"
          >
            Next
          </button>
        </div>

        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}
.modal-content {
  background-color: var(--color-background-soft);
  padding: 0;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
  width: 90%;
  max-width: 450px;
  display: flex;
  flex-direction: column;
  max-height: 70vh;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.8rem 1.2rem;
  border-bottom: 1px solid var(--color-border);
}
.modal-header h4 {
  margin: 0;
  font-size: 1.1em;
  color: var(--color-heading);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.close-btn {
  background: none;
  border: none;
  font-size: 1.8rem;
  color: var(--color-text-light);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.modal-body {
  padding: 1.2rem;
  overflow-y: auto;
}
.loading-message,
.empty-message {
  text-align: center;
  padding: 1rem 0;
  color: var(--color-text-light);
  font-style: italic;
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red);
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}
.success-message {
  color: #155724; /* Dark green */
  background-color: #d4edda; /* Light green */
  border: 1px solid #c3e6cb;
  padding: 0.75rem;
  border-radius: 4px;
  margin-top: 1rem;
  text-align: center;
}
.playlist-selection-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.playlist-item {
  display: flex;
  align-items: center;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--color-border-hover);
}
.playlist-item:last-child {
  border-bottom: none;
}
.playlist-cover-small {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 3px;
  margin-right: 0.75rem;
  background-color: var(--color-background-mute);
}
.playlist-cover-small.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}
.playlist-title {
  flex-grow: 1;
  font-size: 0.95em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.add-button {
  padding: 0.3em 0.7em;
  font-size: 0.85em;
  background-color: var(--color-accent-soft);
  color: var(--color-accent);
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  margin-left: 0.5rem;
  cursor: pointer;
}
.add-button:hover:not(:disabled) {
  background-color: var(--color-accent);
  color: white;
}
.add-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--color-border);
  font-size: 0.9em;
}
.pagination-controls button {
  padding: 0.3rem 0.6rem;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
}
.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
