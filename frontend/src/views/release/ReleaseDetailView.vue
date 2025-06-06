<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink, useRoute } from "vue-router";
import axios from "axios";
import { usePlayerStore } from "@/stores/player";
import { useAuthStore } from "@/stores/auth";
import { useLibraryStore } from "@/stores/library";
import { useCartStore } from "@/stores/cart";
import type { ReleaseDetail, TrackInfoFromApi, PlayerTrackInfo } from "@/types";
import BuyModal from "@/components/shop/BuyModal.vue";
import TrackActionsDropdown from "@/components/track/TrackActionsDropdown.vue"; // Import new component
import AddToPlaylistModal from "@/components/playlist/AddToPlaylistModal.vue"; // Import new modal

const playerStore = usePlayerStore();
const authStore = useAuthStore();
const libraryStore = useLibraryStore();
const cartStore = useCartStore();
const router = useRouter();
const route = useRoute();
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);

const isAddingToLibrary = ref(false);
const addToLibraryError = ref<string | null>(null);

const showBuyModal = ref(false);
const modalError = ref<string | null>(null);

// State for "Add to Playlist" modal
const isAddToPlaylistModalVisible = ref(false);
const trackForPlaylistModal = ref<TrackInfoFromApi | null>(null);

const isOwner = computed(() => {
  if (!authStore.isLoggedIn || !release.value || !authStore.authUser) {
    return false;
  }
  return (
    release.value.artist &&
    release.value.artist.user_id === authStore.authUser.id
  );
});

const isInLibrary = computed(() => {
  if (!release.value || !authStore.isLoggedIn) return false;
  return !!libraryStore.getLibraryItemByReleaseId(release.value.id);
});

const isInCart = computed(() => {
  if (!release.value || !cartStore.cart || !release.value.product_info_id)
    return false;
  return cartStore.cart.items.some(
    (item) => item.product.id === release.value!.product_info_id
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

const formattedMinNypPriceDisplay = computed(() => {
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
  addToLibraryError.value = null;
  modalError.value = null;
  release.value = null;

  try {
    const response = await axios.get<ReleaseDetail>(`/releases/${releaseId}/`);
    release.value = response.data;

    if (authStore.isLoggedIn) {
      if (libraryStore.libraryItems.length === 0) {
        await libraryStore.fetchLibraryItems();
      }
      if (!cartStore.cart) {
        await cartStore.fetchCart();
      }
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

function mapToPlayerTrackInfoUtil(
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
    (apiTrack) => mapToPlayerTrackInfoUtil(apiTrack, release.value!)
  );
  const clickedTrackIndex = allReleasePlayerTracks.findIndex(
    (pt) => pt.id === clickedTrack.id
  );
  if (clickedTrackIndex !== -1) {
    playerStore.setQueueAndPlay(allReleasePlayerTracks, clickedTrackIndex);
  } else {
    playerStore.playTrack(
      mapToPlayerTrackInfoUtil(clickedTrack, release.value!)
    );
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
    (apiTrack) => mapToPlayerTrackInfoUtil(apiTrack, release.value!)
  );
  playerStore.setQueueAndPlay(allReleasePlayerTracks, 0);
};

// Updated: This function is now triggered by TrackActionsDropdown
const handleAddTrackToQueueFromDropdown = (trackToAdd: TrackInfoFromApi) => {
  if (!release.value) return;
  playerStore.addTrackToQueue(
    mapToPlayerTrackInfoUtil(trackToAdd, release.value)
  );
};

// New: Triggered by TrackActionsDropdown to open the modal
const handleOpenAddToPlaylistModalFromDropdown = (track: TrackInfoFromApi) => {
  if (!authStore.isLoggedIn) {
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  trackForPlaylistModal.value = track;
  isAddToPlaylistModalVisible.value = true;
};

const goToEditRelease = () => {
  if (release.value && isOwner.value) {
    router.push({ name: "release-edit", params: { id: release.value.id } });
  }
};

const handleAddFreeItemToLibrary = async () => {
  if (!release.value) return;
  if (!authStore.isLoggedIn) {
    addToLibraryError.value = "Please log in to add items to your library.";
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }

  isAddingToLibrary.value = true;
  addToLibraryError.value = null;
  modalError.value = null;

  const success = await libraryStore.addItemToLibrary(release.value.id, "FREE");
  if (success) {
    // alert(`${release.value.title} has been added to your library!`); // Consider removing alert for better UX
  } else {
    addToLibraryError.value =
      libraryStore.error || "Failed to add free item to library.";
  }
  isAddingToLibrary.value = false;
};

const openBuyModal = () => {
  if (!authStore.isLoggedIn) {
    modalError.value = "Please log in to acquire releases.";
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  if (
    release.value &&
    (release.value.pricing_model === "PAID" ||
      release.value.pricing_model === "NYP")
  ) {
    modalError.value = null;
    showBuyModal.value = true;
  }
};

const handleModalItemAdded = () => {
  // alert(`${release.value?.title} processed successfully! Check your cart or library.`); // Consider removing alert
  if (authStore.isLoggedIn) {
    libraryStore.fetchLibraryItems();
    cartStore.fetchCart();
  }
};

const handleModalError = (errorMessage: string) => {
  modalError.value = errorMessage;
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
            <span
              v-if="
                release.listen_count !== undefined && release.listen_count > 0
              "
              class="listen-count-meta"
            >
              • {{ release.listen_count.toLocaleString() }} plays
            </span>
          </p>
          <p v-if="release.description" class="description">
            {{ release.description }}
          </p>

          <div class="shop-actions">
            <div class="pricing-info">
              <span v-if="release.pricing_model === 'PAID'" class="price-tag">{{
                formattedPrice
              }}</span>
              <span
                v-else-if="release.pricing_model === 'NYP'"
                class="price-tag nyp-label"
                >Name Your Price {{ formattedMinNypPriceDisplay }}</span
              >
              <span
                v-else-if="release.pricing_model === 'FREE'"
                class="price-tag free-label"
                >Free</span
              >
            </div>

            <div v-if="isOwner" class="in-library-message owned-message">
              ✓ This is your release.
            </div>
            <div v-else-if="isInLibrary" class="in-library-message">
              ✓ In Your Library
              <RouterLink :to="{ name: 'library' }" class="library-link"
                >(Go to Library)</RouterLink
              >
            </div>
            <div
              v-else-if="
                isInCart &&
                (release.pricing_model === 'PAID' ||
                  release.pricing_model === 'NYP')
              "
              class="in-cart-message"
            >
              ✓ In Your Cart
              <RouterLink :to="{ name: 'cart' }" class="cart-link"
                >(Go to Cart)</RouterLink
              >
            </div>
            <div v-else>
              <button
                v-if="release.pricing_model === 'FREE'"
                @click="handleAddFreeItemToLibrary"
                class="action-button main-action-button"
                :disabled="isAddingToLibrary"
              >
                {{ isAddingToLibrary ? "Adding..." : "Add to Library (Free)" }}
              </button>
              <button
                v-else-if="
                  release.pricing_model === 'PAID' ||
                  release.pricing_model === 'NYP'
                "
                @click="openBuyModal"
                class="action-button main-action-button buy-button"
              >
                {{
                  release.pricing_model === "PAID"
                    ? `Buy ${formattedPrice}`
                    : "Name Your Price & Buy"
                }}
              </button>
            </div>

            <p v-if="addToLibraryError" class="error-message acquisition-error">
              {{ addToLibraryError }}
            </p>
            <p v-if="modalError" class="error-message acquisition-error">
              {{ modalError }}
            </p>
            <p
              v-if="
                !authStore.isLoggedIn &&
                release.pricing_model !== 'FREE' &&
                !isOwner &&
                !isInLibrary
              "
              class="login-prompt"
            >
              Please
              <RouterLink
                :to="{ name: 'login', query: { redirect: route.fullPath } }"
                >log in</RouterLink
              >
              or <RouterLink :to="{ name: 'register' }">register</RouterLink> to
              acquire this release.
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
            <span
              v-if="track.listen_count !== undefined && track.listen_count > 0"
              class="track-listen-count"
            >
              ({{ track.listen_count.toLocaleString() }} plays)
            </span>
            <span class="track-duration">{{
              formatDuration(track.duration_in_seconds)
            }}</span>
            <!-- Replace existing + button with TrackActionsDropdown -->
            <TrackActionsDropdown
              :track="track"
              :releaseData="release"
              @add-to-queue="handleAddTrackToQueueFromDropdown(track)"
              @open-add-to-playlist-modal="
                handleOpenAddToPlaylistModalFromDropdown(track)
              "
              class="track-item-actions-dropdown"
            />
          </li>
        </ol>
        <p v-else>No tracks found for this release.</p>
      </div>
    </div>
    <div v-else>
      <p>Could not load release data.</p>
    </div>
    <button @click="router.back()" class="back-button">Go Back</button>

    <BuyModal
      v-if="showBuyModal && release"
      :is-visible="showBuyModal"
      :release="release"
      @close="showBuyModal = false"
      @item-added-to-cart="handleModalItemAdded"
      @error-adding-item="handleModalError"
    />

    <!-- Add to Playlist Modal -->
    <AddToPlaylistModal
      :is-visible="isAddToPlaylistModalVisible"
      :track-to-add="trackForPlaylistModal"
      @close="
        isAddToPlaylistModalVisible = false;
        trackForPlaylistModal = null;
      "
      @track-added="
        isAddToPlaylistModalVisible = false;
        trackForPlaylistModal = null;
      "
    />
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
.listen-count-meta {
  font-style: italic;
  color: var(--color-text-light);
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
  color: var(--color-heading);
  font-size: 1.1em;
}
.price-tag.free-label {
  color: #34a853;
}

.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
  align-self: flex-start;
}

.main-action-button {
  background-color: var(--color-accent);
}
.main-action-button:hover {
  background-color: var(--color-accent-hover);
}
.main-action-button:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}
.in-library-message,
.in-cart-message {
  font-size: 1em;
  color: var(--color-text);
  padding: 0.5em;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  align-self: flex-start;
  font-weight: 500;
}
.in-library-message.owned-message {
  background-color: var(--color-background-soft);
  color: var(--color-text-light);
  font-style: italic;
}

.library-link,
.cart-link {
  font-size: 0.9em;
  margin-left: 0.5em;
  font-weight: normal;
  color: var(--color-link);
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
.acquisition-error {
  background-color: var(--vt-c-red-soft);
  border-color: var(--vt-c-red-dark);
  color: var(--vt-c-red-dark);
  padding: 0.5em;
  font-size: 0.9em;
  border-radius: 4px;
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
  gap: 1rem; /* Increased gap for more space */
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
.track-listen-count {
  font-size: 0.8em;
  color: var(--color-text-light);
  margin-left: 0.5em;
  font-style: italic;
}
.track-duration {
  color: var(--color-text-light);
  font-size: 0.9em;
  min-width: 40px; /* Give duration some space */
  text-align: right;
}
/* Styles for the new actions dropdown trigger */
.track-item-actions-dropdown {
  margin-left: auto; /* Push to the far right */
  flex-shrink: 0; /* Prevent shrinking */
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
