// frontend/src/views/LibraryView.vue
<script setup lang="ts">
import { onMounted, computed, ref, onUnmounted, watch } from "vue";
import { useLibraryStore, type LibraryItem } from "@/stores/library";
import { usePlayerStore } from "@/stores/player"; // Keep PlayerTrackInfo here or move to types
import { useAuthStore } from "@/stores/auth";
import { RouterLink } from "vue-router";
import axios from "axios";
import type {
  TrackInfoFromApi,
  GeneratedDownloadStatus,
  PlayerTrackInfo,
} from "@/types";

const libraryStore = useLibraryStore();
const playerStore = usePlayerStore();
const authStore = useAuthStore();

const selectedFormats = ref<Record<number, string>>({});

const libraryItems = computed(() => libraryStore.libraryItems);
const isLoading = computed(() => libraryStore.isLoading);
const error = computed(() => libraryStore.error);

onMounted(() => {
  if (authStore.isLoggedIn) {
    libraryStore.fetchLibraryItems();
  }
});

onUnmounted(() => {
  libraryStore.clearAllPolling();
});

function mapToPlayerTrackInfoFromLibrary(
  apiTrack: TrackInfoFromApi,
  releaseData: LibraryItem["release"]
): PlayerTrackInfo {
  return {
    id: apiTrack.id,
    title: apiTrack.title,
    audio_file: apiTrack.stream_url,
    artistName: releaseData.artist?.name,
    releaseTitle: releaseData.title,
    coverArtUrl: releaseData.cover_art,
    duration: apiTrack.duration_in_seconds,
  };
}

const handlePlayReleaseFromLibrary = (libraryItem: LibraryItem) => {
  if (!libraryItem.release.tracks || libraryItem.release.tracks.length === 0)
    return;
  const allReleasePlayerTracks: PlayerTrackInfo[] =
    libraryItem.release.tracks.map((apiTrack) =>
      mapToPlayerTrackInfoFromLibrary(apiTrack, libraryItem.release)
    );
  playerStore.setQueueAndPlay(allReleasePlayerTracks, 0);
};

const handlePlayTrackFromLibrary = (
  track: TrackInfoFromApi,
  libraryItem: LibraryItem
) => {
  const allReleasePlayerTracks: PlayerTrackInfo[] =
    libraryItem.release.tracks.map((apiTrack) =>
      mapToPlayerTrackInfoFromLibrary(apiTrack, libraryItem.release)
    );
  const clickedTrackIndex = allReleasePlayerTracks.findIndex(
    (pt) => pt.id === track.id
  );
  if (clickedTrackIndex !== -1) {
    playerStore.setQueueAndPlay(allReleasePlayerTracks, clickedTrackIndex);
  }
};

const handleAddReleaseToQueue = (libraryItem: LibraryItem) => {
  if (!libraryItem.release.tracks || libraryItem.release.tracks.length === 0)
    return;
  libraryItem.release.tracks.forEach((apiTrack) => {
    playerStore.addTrackToQueue(
      mapToPlayerTrackInfoFromLibrary(apiTrack, libraryItem.release)
    );
  });
  alert(`${libraryItem.release.title} added to queue.`);
};

const handleRemoveItem = async (libraryItemId: number) => {
  if (confirm("Are you sure you want to remove this item from your library?")) {
    await libraryStore.removeItemFromLibrary(libraryItemId);
  }
};

const handleRequestDownloadForLibraryItem = async (libraryItemId: number) => {
  const format = selectedFormats.value[libraryItemId];
  if (!format) {
    alert("Please select a download format.");
    return;
  }
  await libraryStore.requestLibraryItemDownload(libraryItemId, format);

  const requestStatus = libraryStore.activeDownloadRequests[libraryItemId];
  if (
    requestStatus &&
    (requestStatus.status === "PENDING" ||
      requestStatus.status === "PROCESSING")
  ) {
    libraryStore.startPollingForLibraryItem(libraryItemId, requestStatus.id);
  }
};

const triggerActualDownloadFromLibrary = async (libraryItemId: number) => {
  const downloadStatus = libraryStore.activeDownloadRequests[libraryItemId];
  if (downloadStatus?.download_url) {
    libraryStore.isProcessingDownload[libraryItemId] = true;
    libraryStore.activeDownloadErrors[libraryItemId] = null;
    try {
      const response = await axios.get(downloadStatus.download_url, {
        responseType: "blob",
        headers: {
          Authorization: `Bearer ${authStore.accessToken}`,
        },
      });

      const blob = new Blob([response.data], {
        type: response.headers["content-type"] || "application/zip",
      });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);

      const contentDisposition = response.headers["content-disposition"];
      const libraryEntry = libraryStore.libraryItems.find(
        (item) => item.id === libraryItemId
      );
      let filename = `${libraryEntry?.release.title || "download"}_${
        downloadStatus.requested_format_display
      }.zip`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(link.href);
    } catch (err) {
      console.error("Failed to download file blob from library:", err);
      libraryStore.activeDownloadErrors[libraryItemId] =
        "Could not download the file. Please try again.";
    } finally {
      libraryStore.isProcessingDownload[libraryItemId] = false;
    }
  } else {
    alert("Download URL not available.");
  }
};

const formatAcquisitionType = (
  type: LibraryItem["acquisition_type"]
): string => {
  // Added type for 'type'
  switch (type) {
    case "FREE":
      return "Free";
    case "PURCHASED": // Changed from "PAID" to "PURCHASED" to match model
      return "Purchased";
    case "NYP":
      return "Name Your Price";
    default:
      // This part ensures that if a new type is added to the backend model
      // but not here, it will still display something reasonable (the raw type)
      // and TypeScript will warn you if `type` could be something unexpected.
      const exhaustiveCheck: never = type;
      return exhaustiveCheck;
  }
};

const formatShortDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString();
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

watch(
  libraryItems,
  (newItems) => {
    newItems.forEach((item: LibraryItem) => {
      if (
        !selectedFormats.value[item.id] &&
        item.release.available_download_formats &&
        item.release.available_download_formats.length > 0
      ) {
        selectedFormats.value[item.id] =
          item.release.available_download_formats[0].value;
      }
    });
  },
  { immediate: true, deep: true }
);
</script>

<template>
  <div class="library-view">
    <h2>My Library</h2>

    <div v-if="isLoading" class="loading-message">Loading your library...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="libraryItems.length === 0" class="empty-library">
      Your library is empty. Start by exploring
      <RouterLink :to="{ name: 'releases' }">releases</RouterLink>!
    </div>

    <div v-else class="library-grid">
      <div
        v-for="item in libraryItems"
        :key="item.id"
        class="library-item-card"
      >
        <RouterLink
          :to="{ name: 'release-detail', params: { id: item.release.id } }"
          class="item-main-link"
        >
          <img
            v-if="item.release.cover_art"
            :src="item.release.cover_art"
            :alt="`${item.release.title} cover art`"
            class="item-cover-art"
          />
          <div v-else class="item-cover-art-placeholder">No Cover</div>
          <h3 class="item-title">{{ item.release.title }}</h3>
        </RouterLink>
        <p class="item-artist">
          by
          <RouterLink
            :to="{
              name: 'artist-detail',
              params: { id: item.release.artist.id },
            }"
          >
            {{ item.release.artist.name }}
          </RouterLink>
        </p>
        <p class="item-acquired-info">
          Added: {{ formatShortDate(item.acquired_at) }} ({{
            formatAcquisitionType(item.acquisition_type)
          }})
        </p>

        <div class="item-actions">
          <button
            @click="handlePlayReleaseFromLibrary(item)"
            class="action-btn play-release-btn"
            title="Play Album"
          >
            ▶ Play All
          </button>
          <button
            @click="handleAddReleaseToQueue(item)"
            class="action-btn add-queue-btn"
            title="Add Album to Queue"
          >
            ☰ Add to Queue
          </button>
        </div>

        <!-- Track List within Library Item -->
        <details class="track-list-details">
          <summary>
            Show Tracks ({{ item.release.tracks?.length || 0 }})
          </summary>
          <ol
            v-if="item.release.tracks && item.release.tracks.length > 0"
            class="item-track-list"
          >
            <li
              v-for="track in item.release.tracks"
              :key="track.id"
              class="track-sub-item"
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
              <button
                @click="handlePlayTrackFromLibrary(track, item)"
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
              <span class="track-number">{{ track.track_number || "-" }}.</span>
              <span class="track-title">{{ track.title }}</span>
              <span class="track-duration">{{
                formatDuration(track.duration_in_seconds)
              }}</span>
              <button
                @click="
                  playerStore.addTrackToQueue(
                    mapToPlayerTrackInfoFromLibrary(track, item.release)
                  )
                "
                class="add-queue-button"
                title="Add to Queue"
              >
                +
              </button>
            </li>
          </ol>
        </details>

        <!-- Download Section for each Library Item -->
        <div class="item-download-section">
          <h4>Download Release</h4>
          <div
            v-if="
              item.release.available_download_formats &&
              item.release.available_download_formats.length > 0
            "
          >
            <div class="download-controls">
              <select v-model="selectedFormats[item.id]">
                <option
                  v-for="format in item.release.available_download_formats"
                  :key="format.value"
                  :value="format.value"
                >
                  {{ format.label }}
                </option>
              </select>
              <button
                @click="handleRequestDownloadForLibraryItem(item.id)"
                :disabled="
                  libraryStore.isProcessingDownload[item.id] ||
                  !selectedFormats[item.id] ||
                  (libraryStore.activeDownloadRequests[item.id] &&
                    (libraryStore.activeDownloadRequests[item.id]?.status ===
                      'PENDING' ||
                      libraryStore.activeDownloadRequests[item.id]?.status ===
                        'PROCESSING'))
                "
                class="action-btn request-download-btn"
              >
                {{
                  libraryStore.activeDownloadRequests[item.id] &&
                  (libraryStore.activeDownloadRequests[item.id]?.status ===
                    "PENDING" ||
                    libraryStore.activeDownloadRequests[item.id]?.status ===
                      "PROCESSING")
                    ? "Preparing..."
                    : "Request Download"
                }}
              </button>
            </div>

            <div
              v-if="
                libraryStore.isProcessingDownload[item.id] &&
                !(
                  libraryStore.activeDownloadRequests[item.id] &&
                  (libraryStore.activeDownloadRequests[item.id]?.status ===
                    'PENDING' ||
                    libraryStore.activeDownloadRequests[item.id]?.status ===
                      'PROCESSING')
                )
              "
              class="download-status-message"
            >
              Requesting...
            </div>
            <div
              v-if="libraryStore.activeDownloadErrors[item.id]"
              class="error-message download-specific-error"
            >
              {{ libraryStore.activeDownloadErrors[item.id] }}
            </div>

            <div
              v-if="libraryStore.activeDownloadRequests[item.id]"
              class="download-status-details"
            >
              <p>
                Status:
                <strong>{{
                  libraryStore.activeDownloadRequests[item.id]?.status
                }}</strong>
                ({{
                  libraryStore.activeDownloadRequests[item.id]
                    ?.requested_format_display
                }})
              </p>
              <p
                v-if="
                  libraryStore.activeDownloadRequests[item.id]?.status ===
                  'FAILED'
                "
              >
                Reason:
                {{
                  libraryStore.activeDownloadRequests[item.id]
                    ?.failure_reason || "Unknown"
                }}
              </p>
              <button
                v-if="
                  libraryStore.activeDownloadRequests[item.id]?.status ===
                    'READY' &&
                  libraryStore.activeDownloadRequests[item.id]?.download_url
                "
                @click="triggerActualDownloadFromLibrary(item.id)"
                :disabled="libraryStore.isProcessingDownload[item.id]"
                class="action-btn download-now-btn"
              >
                {{
                  libraryStore.isProcessingDownload[item.id]
                    ? "Downloading..."
                    : "Download Now"
                }}
              </button>
              <p
                v-if="
                  libraryStore.activeDownloadRequests[item.id]?.status ===
                    'READY' &&
                  libraryStore.activeDownloadRequests[item.id]?.expires_at
                "
                class="expiry-note"
              >
                Link expires:
                {{
                  new Date(
                    libraryStore.activeDownloadRequests[item.id]!.expires_at!
                  ).toLocaleString()
                }}
              </p>
            </div>
          </div>
          <p v-else>No download formats specified for this release.</p>
        </div>

        <button
          @click="handleRemoveItem(item.id)"
          class="action-btn remove-item-btn"
          title="Remove from Library"
        >
          🗑️ Remove
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.library-view {
  max-width: 1200px;
  margin: 1rem auto;
  padding: 1rem;
}
.library-view h2 {
  text-align: center;
  margin-bottom: 2rem;
}
.loading-message,
.empty-library {
  text-align: center;
  font-style: italic;
  padding: 2rem;
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

.library-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.library-item-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.item-main-link {
  text-decoration: none;
  color: inherit;
}
.item-cover-art,
.item-cover-art-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-background-mute);
  margin-bottom: 0.5rem;
}
.item-cover-art-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9em;
  color: var(--color-text-light);
}
.item-title {
  font-size: 1.2em;
  font-weight: 600;
  color: var(--color-heading);
  margin: 0.3rem 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-artist {
  font-size: 0.95em;
  color: var(--color-text);
}
.item-artist a {
  color: var(--color-text-light);
  text-decoration: none;
}
.item-artist a:hover {
  text-decoration: underline;
  color: var(--color-link);
}
.item-acquired-info {
  font-size: 0.8em;
  color: var(--color-text-light);
  margin-bottom: 0.5rem;
}

.item-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}
.action-btn {
  padding: 0.4em 0.8em;
  font-size: 0.85em;
  border-radius: 4px;
  cursor: pointer;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.action-btn:hover {
  border-color: var(--color-accent);
}
.play-release-btn {
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border-color: var(--color-accent);
}
.play-release-btn:hover {
  background-color: var(--color-accent-hover);
}
.remove-item-btn {
  margin-top: auto; /* Pushes to bottom if other actions wrap */
  align-self: flex-start; /* Aligns with other buttons if they are on the same line */
  background-color: var(--vt-c-red-soft);
  border-color: var(--vt-c-red-dark);
  color: var(--vt-c-red-dark);
}
.remove-item-btn:hover {
  background-color: var(--vt-c-red);
  color: var(--vt-c-white);
}

.track-list-details {
  margin-top: 0.8rem;
  font-size: 0.9em;
}
.track-list-details summary {
  cursor: pointer;
  font-weight: 500;
  padding: 0.3em 0;
  color: var(--color-text);
}
.item-track-list {
  list-style: none;
  padding-left: 0.5rem; /* Indent tracks slightly */
  margin-top: 0.5rem;
}
.track-sub-item {
  display: flex;
  align-items: center;
  padding: 0.5rem 0.2rem;
  border-top: 1px solid var(--color-border-hover);
  gap: 0.5rem;
}
.track-sub-item:first-child {
  border-top: none;
}
.track-sub-item.is-playing .track-title,
.track-sub-item.is-paused .track-title {
  color: var(--color-accent);
  font-weight: 600;
}
.play-icon-button {
  background: none;
  border: none;
  color: var(--color-accent);
  font-size: 1em;
  cursor: pointer;
  padding: 0 0.2em;
  width: 20px;
  text-align: center;
}
.track-number {
  color: var(--color-text-light);
  min-width: 1.5em;
  text-align: right;
  font-size: 0.9em;
}
.track-title {
  flex-grow: 1;
  font-size: 0.95em;
}
.track-duration {
  color: var(--color-text-light);
  font-size: 0.9em;
}
.add-queue-button {
  font-size: 0.9em;
  padding: 0.1em 0.4em;
  border-radius: 50%;
  line-height: 1;
  min-width: 20px;
  min-height: 20px;
}

.item-download-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px dashed var(--color-border);
}
.item-download-section h4 {
  font-size: 1em;
  font-weight: 500;
  margin-bottom: 0.5rem;
}
.download-controls {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}
.download-controls select {
  padding: 0.4em;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
  flex-grow: 1;
}
.request-download-btn,
.download-now-btn {
  font-size: 0.9em;
}
.download-status-message {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text-light);
  margin-top: 0.3rem;
}
.download-specific-error {
  font-size: 0.85em;
  margin-top: 0.3rem;
}
.download-status-details {
  margin-top: 0.5rem;
  font-size: 0.85em;
  background-color: var(--color-background);
  padding: 0.5rem;
  border-radius: 4px;
}
.download-status-details p {
  margin: 0.2rem 0;
}
.download-status-details strong {
  color: var(--color-heading);
}
.expiry-note {
  font-size: 0.8em;
  color: var(--color-text-light);
}
</style>
