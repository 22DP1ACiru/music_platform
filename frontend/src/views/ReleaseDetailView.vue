<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink } from "vue-router";
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
  audio_file: string;
  stream_url: string;
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
  // New shop fields
  download_file: string | null; // URL to the download file
  pricing_model: "FREE" | "PAID" | "NYP";
  pricing_model_display: string;
  price: string | null; // Comes as string from API (DecimalField)
  currency: string | null;
  minimum_price_nyp: string | null; // Comes as string
}

const playerStore = usePlayerStore();
const authStore = useAuthStore();
const router = useRouter();
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);
const nypAmount = ref<string>(""); // For NYP input

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

const handleDownload = () => {
  if (release.value?.download_file) {
    // For direct download, ensure the URL is correct.
    // If it's a relative URL from the API (e.g., /media/downloads/file.zip),
    // prepend the API base URL if not already handled by Axios default or browser.
    let downloadUrl = release.value.download_file;
    if (!downloadUrl.startsWith("http")) {
      const apiUrl = axios.defaults.baseURL || window.location.origin;
      downloadUrl = `${apiUrl.replace("/api", "")}${downloadUrl}`; // Adjust if /api is part of baseURL
    }
    console.log("Attempting to download from:", downloadUrl);
    window.open(downloadUrl, "_blank");
  } else {
    alert("No download file available.");
  }
};

const handlePurchase = () => {
  // This is where you'd initiate the payment flow.
  // For "Paid", you know the price. For "NYP", use nypAmount.value.
  // 1. Validate nypAmount if NYP.
  // 2. Create an order on the backend.
  // 3. Redirect to payment gateway.
  // (This is a placeholder for a much larger feature)
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
      )} ${paymentCurrency}. \n(Payment gateway integration needed)`
    );
    // Example: Create an order then redirect
    // const orderData = { release_id: release.value.id, amount: amountToPay, currency: paymentCurrency };
    // axios.post('/shop/create-order/', orderData).then(response => { /* redirect to payment */ });
  } else {
    alert("Pricing information is unclear for purchase.");
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

          <!-- Download/Purchase Section -->
          <div class="shop-actions" v-if="release.download_file">
            <div v-if="release.pricing_model === 'FREE'" class="price-display">
              <button
                @click="handleDownload"
                class="action-button download-button"
              >
                Download (Free)
              </button>
            </div>
            <div
              v-else-if="release.pricing_model === 'PAID'"
              class="price-display"
            >
              <span>{{ formattedPrice }}</span>
              <button
                @click="handlePurchase"
                class="action-button purchase-button"
              >
                Buy Download
              </button>
            </div>
            <div
              v-else-if="release.pricing_model === 'NYP'"
              class="price-display nyp-section"
            >
              <label for="nyp-amount"
                >Name Your Price {{ formattedMinNypPrice }}:</label
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
                <!-- <span class="nyp-currency-label">{{ release.currency }}</span> -->
              </div>
              <button
                @click="handlePurchase"
                class="action-button purchase-button"
              >
                Pay & Download
              </button>
            </div>
            <p class="pricing-model-note">
              Download Pricing: {{ release.pricing_model_display }}
            </p>
          </div>
          <div v-else class="shop-actions">
            <p>Download not yet available for this release.</p>
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
}
.price-display {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}
.price-display span:first-child {
  /* For fixed price display */
  font-size: 1.2em;
  font-weight: bold;
  color: var(--color-accent);
}
.nyp-section {
  flex-direction: column;
  align-items: flex-start;
}
.nyp-section label {
  font-size: 0.95em;
  margin-bottom: 0.3rem;
}
.nyp-input-group {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.nyp-input-group .currency-symbol {
  font-size: 1.1em;
}
.nyp-input-group input[type="number"] {
  padding: 0.4rem 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  width: 100px; /* Adjust as needed */
  text-align: right;
}
/* .nyp-input-group .nyp-currency-label {
    font-size: 0.9em;
    color: var(--color-text-light);
} */
.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
}
.download-button {
  background-color: var(
    --color-accent-hover
  ); /* A slightly different shade or distinct color */
}
.download-button:hover {
  background-color: var(--color-accent);
}
.purchase-button {
  background-color: var(--color-accent);
}
.purchase-button:hover {
  background-color: var(--color-accent-hover);
}
.pricing-model-note {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text-light);
  margin-top: 0.5rem;
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
