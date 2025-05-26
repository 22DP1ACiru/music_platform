// frontend/src/views/ReleaseDetailView.vue
<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { useRouter, RouterLink, useRoute } from "vue-router";
import axios from "axios";
import { usePlayerStore } from "@/stores/player";
import { useAuthStore } from "@/stores/auth";
import { useLibraryStore } from "@/stores/library";
import type { ReleaseDetail, TrackInfoFromApi, PlayerTrackInfo } from "@/types";

const playerStore = usePlayerStore();
const authStore = useAuthStore();
const libraryStore = useLibraryStore();
const router = useRouter();
const route = useRoute();
const release = ref<ReleaseDetail | null>(null);
const props = defineProps<{ id: string | string[] }>();
const isLoading = ref(true);
const error = ref<string | null>(null);
const nypAmount = ref<string>("");

const isAddingToLibrary = ref(false);
const addToLibraryError = ref<string | null>(null);

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
  addToLibraryError.value = null;
  release.value = null;

  try {
    const response = await axios.get<ReleaseDetail>(`/releases/${releaseId}/`);
    release.value = response.data;
    if (release.value?.pricing_model === "NYP") {
      nypAmount.value = release.value.minimum_price_nyp
        ? parseFloat(release.value.minimum_price_nyp).toFixed(2)
        : "0.00";
    }
    if (authStore.isLoggedIn && libraryStore.libraryItems.length === 0) {
      await libraryStore.fetchLibraryItems();
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

const handleAddTrackToQueue = (trackToAdd: TrackInfoFromApi) => {
  if (!release.value) return;
  playerStore.addTrackToQueue(
    mapToPlayerTrackInfoUtil(trackToAdd, release.value)
  );
};

const goToEditRelease = () => {
  if (release.value && isOwner.value) {
    router.push({ name: "release-edit", params: { id: release.value.id } });
  }
};

const handleAcquireRelease = async () => {
  if (!release.value) return;
  if (!authStore.isLoggedIn) {
    addToLibraryError.value = "Please log in to add items to your library.";
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  // Artist self-acquisition check:
  // This logic should ideally be on the backend or more robustly handled.
  // For now, a simple frontend check:
  if (isOwner.value) {
    // Instead of error, let's try adding it as FREE acquisition if owner
    // Or simply disallow "acquiring" own items via purchase flow.
    // For simplicity, if owner, we might assume it's already "in library" conceptually.
    // Let's try adding it as FREE if they click and are owner.
    // This is similar to how library "add-item" works for free items or owners.
    isAddingToLibrary.value = true;
    addToLibraryError.value = null;
    const addedViaLibrary = await libraryStore.addItemToLibrary(
      release.value.id,
      "FREE"
    );
    if (addedViaLibrary) {
      alert("As the artist, this release is available in your library.");
    } else {
      addToLibraryError.value =
        libraryStore.error || "Could not update library status.";
    }
    isAddingToLibrary.value = false;
    return;
  }

  isAddingToLibrary.value = true;
  addToLibraryError.value = null;

  // If the product is FREE, use the existing libraryStore.addItemToLibrary
  if (release.value.pricing_model === "FREE") {
    const success = await libraryStore.addItemToLibrary(
      release.value.id,
      "FREE"
    );
    if (success) {
      alert(`${release.value.title} has been added to your library!`);
    } else {
      addToLibraryError.value =
        libraryStore.error || "Failed to add free item to library.";
    }
    isAddingToLibrary.value = false;
    return;
  }

  // For PAID or NYP, proceed with order creation
  const orderPayloadItems: any[] = [];
  let itemPriceForOrder: number | undefined = undefined;

  if (release.value.pricing_model === "PAID") {
    // For PAID, price_override is not strictly needed if backend defaults to product.price
    // but can be explicit. For now, let's not send price_override for PAID.
  } else if (release.value.pricing_model === "NYP") {
    const enteredAmount = parseFloat(nypAmount.value);
    const minAmount = release.value.minimum_price_nyp
      ? parseFloat(release.value.minimum_price_nyp)
      : 0;
    if (isNaN(enteredAmount) || enteredAmount < minAmount) {
      addToLibraryError.value = `Please enter an amount of at least ${minAmount.toFixed(
        2
      )} ${release.value.currency || "USD"}.`;
      isAddingToLibrary.value = false;
      return;
    }
    itemPriceForOrder = enteredAmount;
  }

  if (!release.value.product_info_id) {
    addToLibraryError.value =
      "Product information not found for this release. Cannot acquire.";
    isAddingToLibrary.value = false;
    return;
  }

  // We need product.id. Assume release.id can map to product.id on backend (via signal)
  // OR, if ReleaseSerializer includes product_info.id, use that.
  // For now, assuming the first product related to the release is the one to buy.
  // This needs to be robust: fetch product_id associated with this release.
  // Let's assume for now release.id IS effectively the key to find the Product.
  // The backend OrderItemCreateSerializer uses product_id.
  // The Product is created from Release, so Product.release_id = Release.id
  // We need to find the Product.id whose release_id matches release.value.id.
  // This info is not directly on ReleaseDetail.vue.
  // Easiest: modify ReleaseSerializer to include `product_info_id = serializers.ReadOnlyField(source='product_info.id')`

  // TEMPORARY: This is a placeholder. You MUST get the actual Product ID.
  // For the signal `create_or_update_product_from_release`, the Product.release is a OneToOneField.
  // So, if a Product exists for this Release, we need its ID.
  // The frontend might not know the Product ID directly.
  // The OrderItemCreateSerializer expects `product_id`.
  // Simplification: Let's assume backend ReleaseSerializer is modified to return `product_info: { id: <product_id> }`
  // Or, have a dedicated endpoint to get Product ID for a Release ID.

  // For now, let's assume the ReleaseSerializer includes product_info.id as `product_id_on_release`
  // if (!release.value.product_id_on_release) { // You'd add this field to ReleaseDetail type
  //   addToLibraryError.value = "Product information not found for this release.";
  //   isAddingToLibrary.value = false;
  //   return;
  // }

  const orderItem: any = {
    // product_id: release.value.product_id_on_release, // Replace with actual product ID logic
    // HACK: For now, let's assume the Release ID itself is enough for backend to find the Product
    // This is NOT how the OrderItemCreateSerializer is written (it expects product_id).
    // To make this work with current serializer, we need the Product ID.
    // The simplest way is to add `product_info_id = serializers.IntegerField(source='product_info.id', read_only=True)` to `ReleaseSerializer`
    // and update `ReleaseDetail` type in frontend.
    // Let's assume this is done and `release.value.product_info_id` exists.

    product_id: release.value.product_info_id,
    // The Product model has a release_id. Backend will need to look up Product by release_id
    // if we send release.id here. This requires backend serializer change.
    // OR frontend needs the actual Product ID.

    quantity: 1,
  };
  if (
    release.value.pricing_model === "NYP" &&
    itemPriceForOrder !== undefined
  ) {
    orderItem.price_override = itemPriceForOrder.toFixed(2);
  }

  orderPayloadItems.push(orderItem);

  try {
    await axios.post("/shop/orders/", { items: orderPayloadItems });
    alert(
      `${release.value.title} has been acquired and added to your library!`
    );
    // Refresh library items
    await libraryStore.fetchLibraryItems();
  } catch (err: any) {
    if (axios.isAxiosError(err) && err.response) {
      const errorData = err.response.data;
      if (
        errorData.items &&
        errorData.items[0] &&
        errorData.items[0].price_override
      ) {
        addToLibraryError.value = `NYP Error: ${errorData.items[0].price_override.join(
          ", "
        )}`;
      } else if (
        errorData.items &&
        errorData.items[0] &&
        errorData.items[0].product_id
      ) {
        addToLibraryError.value = `Product Error: ${errorData.items[0].product_id.join(
          ", "
        )}`;
      } else if (errorData.currency) {
        addToLibraryError.value = `Currency Error: ${errorData.currency.join(
          ", "
        )}`;
      } else {
        addToLibraryError.value =
          err.response.data.detail || "Could not process acquisition.";
      }
    } else {
      addToLibraryError.value = "An unexpected error occurred.";
    }
    console.error("Error acquiring release:", err);
  } finally {
    isAddingToLibrary.value = false;
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

          <!-- Acquisition Section -->
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
                >Free</span
              >
            </div>

            <div
              v-if="release.pricing_model === 'NYP' && !isInLibrary && !isOwner"
              class="nyp-input-area"
            >
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

            <button
              v-if="!isInLibrary && !isOwner"
              @click="handleAcquireRelease"
              class="action-button main-action-button"
              :disabled="
                isAddingToLibrary ||
                (!authStore.isLoggedIn && release.pricing_model !== 'FREE')
              "
            >
              {{
                isAddingToLibrary
                  ? "Processing..."
                  : release.pricing_model === "FREE"
                  ? "Add to Library"
                  : !authStore.isLoggedIn
                  ? "Login to Acquire"
                  : "Acquire Release"
              }}
            </button>
            <div v-else-if="isOwner" class="in-library-message owned-message">
              ✓ You are the artist of this release.
            </div>
            <div v-else-if="isInLibrary" class="in-library-message">
              ✓ In Your Library
              <RouterLink :to="{ name: 'library' }" class="library-link"
                >(Go to Library)</RouterLink
              >
            </div>

            <p v-if="addToLibraryError" class="error-message acquisition-error">
              {{ addToLibraryError }}
            </p>
            <p class="pricing-model-note">
              Acquisition type: {{ release.pricing_model_display }}
            </p>
            <p
              v-if="
                !authStore.isLoggedIn &&
                release.pricing_model !== 'FREE' &&
                !isOwner
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
  color: var(--color-heading);
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

.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  color: white;
}

.main-action-button {
  background-color: var(--color-accent);
  align-self: flex-start;
}
.main-action-button:hover {
  background-color: var(--color-accent-hover);
}
.main-action-button:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}
.in-library-message {
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

.library-link {
  font-size: 0.9em;
  margin-left: 0.5em;
  font-weight: normal;
  color: var(--color-link);
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
.acquisition-error {
  background-color: var(--vt-c-red-soft);
  border-color: var(--vt-c-red-dark);
  color: var(--vt-c-red-dark);
  padding: 0.5em;
  font-size: 0.9em;
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
