<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink, useRoute } from "vue-router"; // Added useRoute
import axios from "axios";
import { usePlayerStore, type PlayerTrackInfo } from "@/stores/player";
import { useAuthStore } from "@/stores/auth";

interface ArtistInfo {
  id: number;
  name: string;
  user_id: number;
}

interface TrackInfoFromApi {
  id: number;
  title: string;
  track_number: number | null;
  duration_in_seconds: number | null;
  audio_file: string; // This is the original upload path, for reference
  stream_url: string; // This is the streaming URL
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
  pricing_model: "FREE" | "PAID" | "NYP";
  pricing_model_display: string;
  price: string | null;
  currency: string | null;
  minimum_price_nyp: string | null;
  available_download_formats: { value: string; label: string }[];
}

interface GeneratedDownloadStatus {
  id: number;
  unique_identifier: string;
  release: number;
  release_title: string;
  user: number;
  requested_format: string;
  requested_format_display: string;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED" | "EXPIRED";
  celery_task_id: string | null;
  download_url: string | null; // This is the API URL to fetch the file
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  failure_reason: string | null;
}

const playerStore = usePlayerStore();
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute(); // Get current route for redirect query param
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);
const nypAmount = ref<string>("");

const selectedDownloadFormat = ref<string>("");
const isRequestingDownload = ref(false);
const downloadRequestStatus = ref<GeneratedDownloadStatus | null>(null);
const downloadStatusError = ref<string | null>(null);
let pollIntervalId: number | undefined;

const isOwner = computed(() => {
  if (!authStore.isLoggedIn || !release.value || !authStore.authUser) {
    return false;
  }
  return (
    release.value.artist &&
    release.value.artist.user_id === authStore.authUser.id
  );
});

const formattedPrice = computed(() => {
  if (
    release.value?.pricing_model === "PAID" &&
    release.value.price &&
    release.value.currency
  ) {
    const priceNum = parseFloat(release.value.price);
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: release.value.currency,
    }).format(priceNum);
  }
  return "";
});

const formattedMinNypPrice = computed(() => {
  if (
    release.value?.pricing_model === "NYP" &&
    release.value.minimum_price_nyp &&
    release.value.currency
  ) {
    const priceNum = parseFloat(release.value.minimum_price_nyp);
    if (priceNum > 0) {
      return `(Minimum ${new Intl.NumberFormat(undefined, {
        style: "currency",
        currency: release.value.currency,
      }).format(priceNum)})`;
    }
  }
  return "(Enter 0 or more)";
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
  selectedDownloadFormat.value = "";
  stopPollingDownloadStatus();
  downloadRequestStatus.value = null;
  downloadStatusError.value = null;

  try {
    const response = await axios.get<ReleaseDetail>(`/releases/${releaseId}/`);
    release.value = response.data;
    if (
      release.value?.pricing_model === "NYP" &&
      release.value.minimum_price_nyp
    ) {
      nypAmount.value = parseFloat(release.value.minimum_price_nyp).toFixed(2);
    } else if (release.value?.pricing_model === "NYP") {
      nypAmount.value = "0.00";
    }
    if (
      release.value?.available_download_formats &&
      release.value.available_download_formats.length > 0
    ) {
      selectedDownloadFormat.value =
        release.value.available_download_formats[0].value;
    }
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

function mapToPlayerTrackInfo(
  apiTrack: TrackInfoFromApi,
  releaseData: ReleaseDetail
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

const handleRequestDownload = async () => {
  if (!release.value || !selectedDownloadFormat.value) {
    downloadStatusError.value = "Please select a download format.";
    return;
  }
  if (!authStore.isLoggedIn) {
    downloadStatusError.value = "Please log in to request a download.";
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }

  isRequestingDownload.value = true;
  downloadStatusError.value = null;
  downloadRequestStatus.value = null;

  try {
    const response = await axios.post<GeneratedDownloadStatus>(
      `/releases/${release.value.id}/request_download/`,
      { requested_format: selectedDownloadFormat.value }
    );
    downloadRequestStatus.value = response.data;
    if (
      response.data.status === "PENDING" ||
      response.data.status === "PROCESSING"
    ) {
      startPollingDownloadStatus(response.data.id);
    }
  } catch (err: any) {
    console.error("Failed to request download:", err);
    if (axios.isAxiosError(err) && err.response) {
      downloadStatusError.value =
        err.response.data.detail || "Failed to start download preparation.";
    } else {
      downloadStatusError.value = "An unexpected error occurred.";
    }
  } finally {
    isRequestingDownload.value = false;
  }
};

const pollDownloadStatus = async (downloadId: number) => {
  if (
    !downloadRequestStatus.value ||
    downloadRequestStatus.value.id !== downloadId
  ) {
    try {
      const initialStatusResponse = await axios.get<GeneratedDownloadStatus>(
        `/generated-download-status/${downloadId}/`
      );
      downloadRequestStatus.value = initialStatusResponse.data;
    } catch (err) {
      console.error(
        "Poll: Failed to fetch initial download status for ID:",
        downloadId,
        err
      );
      downloadStatusError.value = "Could not retrieve download status.";
      stopPollingDownloadStatus();
      return;
    }
  }

  if (
    !downloadRequestStatus.value ||
    downloadRequestStatus.value.status === "READY" ||
    downloadRequestStatus.value.status === "FAILED" ||
    downloadRequestStatus.value.status === "EXPIRED"
  ) {
    stopPollingDownloadStatus();
    return;
  }

  try {
    const response = await axios.get<GeneratedDownloadStatus>(
      `/generated-download-status/${downloadRequestStatus.value.id}/` // Use the ID from the status object
    );
    downloadRequestStatus.value = response.data;
    if (
      response.data.status === "READY" ||
      response.data.status === "FAILED" ||
      response.data.status === "EXPIRED"
    ) {
      stopPollingDownloadStatus();
    }
  } catch (err) {
    console.error("Polling error:", err);
    downloadStatusError.value = "Error checking download status.";
  }
};

const startPollingDownloadStatus = (downloadId: number) => {
  stopPollingDownloadStatus();
  pollDownloadStatus(downloadId);
  pollIntervalId = window.setInterval(
    () => pollDownloadStatus(downloadId),
    5000
  );
};

const stopPollingDownloadStatus = () => {
  if (pollIntervalId) {
    clearInterval(pollIntervalId);
    pollIntervalId = undefined;
  }
};

const triggerActualDownload = async () => {
  if (downloadRequestStatus.value?.download_url) {
    isRequestingDownload.value = true; // Use this to show loading state on button
    downloadStatusError.value = null;
    try {
      // The download_url is the API endpoint that serves the file
      const response = await axios.get(
        downloadRequestStatus.value.download_url,
        {
          responseType: "blob", // Important: Set responseType to 'blob'
        }
      );

      const blob = new Blob([response.data], {
        type: response.headers["content-type"] || "application/zip",
      });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);

      // Try to get filename from Content-Disposition header, fallback to constructing one
      const contentDisposition = response.headers["content-disposition"];
      let filename = `${release.value?.title || "download"}_${
        downloadRequestStatus.value.requested_format_display
      }.zip`; // Fallback
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
      console.error("Failed to download file blob:", err);
      downloadStatusError.value =
        "Could not download the file. Please try again.";
    } finally {
      isRequestingDownload.value = false;
    }
  } else {
    alert("Download URL not available.");
  }
};

const handlePurchaseOrGetFree = () => {
  if (release.value?.pricing_model === "FREE") {
    if (
      release.value.available_download_formats &&
      release.value.available_download_formats.length > 0
    ) {
      if (!selectedDownloadFormat.value) {
        selectedDownloadFormat.value =
          release.value.available_download_formats[0].value;
      }
      handleRequestDownload();
    } else {
      alert("No download formats available for this free release.");
    }
  } else {
    let amountToPay: number | null = null;
    let paymentCurrency = release.value?.currency;

    if (release.value?.pricing_model === "PAID" && release.value.price) {
      amountToPay = parseFloat(release.value.price);
    } else if (release.value?.pricing_model === "NYP") {
      const enteredAmount = parseFloat(nypAmount.value);
      const minAmount = release.value.minimum_price_nyp
        ? parseFloat(release.value.minimum_price_nyp)
        : 0;
      if (isNaN(enteredAmount) || enteredAmount < minAmount) {
        alert(
          `Please enter an amount of at least ${minAmount.toFixed(
            2
          )} ${paymentCurrency}.`
        );
        return;
      }
      amountToPay = enteredAmount;
    }

    if (amountToPay !== null && paymentCurrency) {
      alert(
        `Initiate purchase for ${release.value?.title} at ${amountToPay.toFixed(
          2
        )} ${paymentCurrency}. \n(Payment gateway integration needed)\nAfter successful payment, the download preparation would start.`
      );
      // TODO: After successful payment in a real scenario:
      // handleRequestDownload();
    } else {
      alert("Pricing information is unclear for purchase.");
    }
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

watch(
  () => authStore.isLoggedIn,
  (loggedIn) => {
    if (!loggedIn) {
      stopPollingDownloadStatus();
      downloadRequestStatus.value = null;
    }
  }
);

import { onUnmounted } from "vue";
onUnmounted(() => {
  stopPollingDownloadStatus();
});

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

          <!-- Download/Purchase Section -->
          <div class="shop-actions">
            <div class="pricing-info">
              <span v-if="release.pricing_model === 'PAID'" class="price-tag">{{
                formattedPrice
              }}</span>
              <span
                v-else-if="release.pricing_model === 'NYP'"
                class="price-tag nyp-label"
                >Name Your Price</span
              >
              <span
                v-else-if="release.pricing_model === 'FREE'"
                class="price-tag free-label"
                >Free Download</span
              >
            </div>

            <div v-if="release.pricing_model === 'NYP'" class="nyp-input-area">
              <label for="nyp-amount" class="nyp-amount-label"
                >Enter amount {{ formattedMinNypPrice }}:</label
              >
              <div class="nyp-input-group">
                <span class="currency-symbol">{{
                  release.currency === "EUR"
                    ? "€"
                    : release.currency === "GBP"
                    ? "£"
                    : "$"
                }}</span>
                <input
                  type="number"
                  id="nyp-amount"
                  v-model="nypAmount"
                  step="0.01"
                  min="0"
                />
              </div>
            </div>

            <div
              class="download-format-selector"
              v-if="
                release.available_download_formats &&
                release.available_download_formats.length > 0 &&
                authStore.isLoggedIn /* Show selector only if logged in or if it's a FREE item potentially */
              "
            >
              <label for="download-format">Download format:</label>
              <select id="download-format" v-model="selectedDownloadFormat">
                <option
                  v-for="format in release.available_download_formats"
                  :key="format.value"
                  :value="format.value"
                >
                  {{ format.label }}
                </option>
              </select>
            </div>

            <button
              @click="handlePurchaseOrGetFree"
              class="action-button main-action-button"
              :disabled="
                isRequestingDownload ||
                (downloadRequestStatus &&
                  (downloadRequestStatus.status === 'PENDING' ||
                    downloadRequestStatus.status === 'PROCESSING')) ||
                (!authStore.isLoggedIn &&
                  release.pricing_model !==
                    'FREE') /* Disable if not logged in and not free */
              "
            >
              {{
                !authStore.isLoggedIn && release.pricing_model !== "FREE"
                  ? "Login to Purchase"
                  : release.pricing_model === "FREE"
                  ? "Get Download"
                  : "Buy Now"
              }}
            </button>
            <p class="pricing-model-note">
              Pricing: {{ release.pricing_model_display }}
            </p>

            <!-- Download Status/Link Area -->
            <div v-if="authStore.isLoggedIn">
              <div
                v-if="
                  isRequestingDownload &&
                  !(
                    downloadRequestStatus &&
                    (downloadRequestStatus.status === 'PENDING' ||
                      downloadRequestStatus.status === 'PROCESSING')
                  )
                "
                class="download-status"
              >
                Requesting download preparation...
              </div>
              <div
                v-if="downloadStatusError"
                class="error-message download-error"
              >
                {{ downloadStatusError }}
              </div>
              <div v-if="downloadRequestStatus" class="download-status">
                <p>
                  Status ({{ downloadRequestStatus.requested_format_display }}):
                  <strong>{{ downloadRequestStatus.status }}</strong>
                </p>
                <p
                  v-if="
                    downloadRequestStatus.status === 'PENDING' ||
                    downloadRequestStatus.status === 'PROCESSING'
                  "
                >
                  Your download is being prepared. This may take a few moments.
                </p>
                <p v-if="downloadRequestStatus.status === 'FAILED'">
                  Reason:
                  {{ downloadRequestStatus.failure_reason || "Unknown error" }}
                  <button
                    @click="handleRequestDownload"
                    :disabled="isRequestingDownload"
                    class="action-button retry-button"
                  >
                    Retry
                  </button>
                </p>
                <button
                  v-if="
                    downloadRequestStatus.status === 'READY' &&
                    downloadRequestStatus.download_url
                  "
                  @click="triggerActualDownload"
                  class="action-button download-ready-button"
                  :disabled="isRequestingDownload"
                >
                  {{
                    isRequestingDownload
                      ? "Downloading..."
                      : `Download Now (${downloadRequestStatus.requested_format_display})`
                  }}
                </button>
                <p
                  v-if="
                    downloadRequestStatus.status === 'READY' &&
                    downloadRequestStatus.expires_at
                  "
                  class="expiry-note"
                >
                  Link expires:
                  {{
                    new Date(downloadRequestStatus.expires_at).toLocaleString()
                  }}
                </p>
                <p
                  v-if="downloadRequestStatus.status === 'EXPIRED'"
                  class="expiry-note"
                >
                  This download link has expired.
                  <button
                    @click="handleRequestDownload"
                    :disabled="isRequestingDownload"
                    class="action-button retry-button"
                  >
                    Request New Link
                  </button>
                </p>
              </div>
            </div>
            <p
              v-else-if="release.pricing_model !== 'FREE'"
              class="login-prompt"
            >
              Please
              <RouterLink
                :to="{ name: 'login', query: { redirect: route.fullPath } }"
                >log in</RouterLink
              >
              or <RouterLink :to="{ name: 'register' }">register</RouterLink> to
              purchase and download.
            </p>
          </div>

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
                playerStore.currentTrack?.id === track.id,
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

.shop-actions {
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.pricing-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.price-tag {
  font-size: 1.3em;
  font-weight: bold;
  color: var(--color-accent);
}
.price-tag.nyp-label {
  color: var(--color-heading); /* Or a different accent */
}
.price-tag.free-label {
  color: #34a853; /* Green for free */
}

.nyp-input-area {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.5rem;
}
.nyp-amount-label {
  font-size: 0.9em;
  color: var(--color-text-light);
}
.nyp-input-group {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.nyp-input-group .currency-symbol {
  font-size: 1.1em;
  padding-right: 0.1em;
}
.nyp-input-group input[type="number"] {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  width: 100px;
  text-align: right;
  background-color: var(--color-background);
  color: var(--color-text);
}

.download-format-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9em;
}
.download-format-selector label {
  color: var(--color-text-light);
}
.download-format-selector select {
  padding: 0.3em 0.5em;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
}

.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
}
.retry-button {
  /* Specific style for retry buttons */
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.retry-button:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
.main-action-button {
  background-color: var(--color-accent);
  align-self: flex-start; /* Align button to the start of the flex container */
}
.main-action-button:hover {
  background-color: var(--color-accent-hover);
}
.main-action-button:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}

.pricing-model-note {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text-light);
  margin-top: 0.25rem;
}
.login-prompt {
  font-size: 0.9em;
  color: var(--color-text);
  margin-top: 0.5rem;
}
.login-prompt a {
  color: var(--color-link);
  text-decoration: underline;
}

.download-status {
  margin-top: 0.75rem;
  padding: 0.75rem;
  border: 1px dashed var(--color-border-hover);
  border-radius: 4px;
  font-size: 0.9em;
}
.download-status p {
  margin: 0.3rem 0;
}
.download-status strong {
  color: var(--color-heading);
}
.download-status button {
  /* Style for retry/download now buttons within status */
  margin-left: 0.5rem;
  font-size: 0.9em;
  padding: 0.2em 0.5em;
}
.download-ready-button {
  background-color: #28a745; /* Green for ready */
}
.download-ready-button:hover {
  background-color: #218838;
}
.download-ready-button:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}
.download-error {
  background-color: var(--vt-c-red-soft);
  border-color: var(--vt-c-red-dark);
  color: var(--vt-c-red-dark);
}
.expiry-note {
  font-size: 0.8em;
  color: var(--color-text-light);
  margin-top: 0.3rem;
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
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.play-all-button {
  background-color: var(--color-accent);
  color: white;
}
.play-all-button:hover {
  background-color: var(--color-accent-hover);
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
  color: var(--color-accent);
  font-weight: 600;
}

.play-icon-button {
  background: none;
  border: none;
  color: var(--color-accent);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.2em 0.4em;
  width: 28px;
  text-align: center;
}
.play-icon-button:hover {
  color: var(--color-accent-hover);
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
  font-size: 1em;
  line-height: 1;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  color: var(--color-text);
  margin-left: 0.5rem;
  cursor: pointer;
  min-width: 28px;
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
