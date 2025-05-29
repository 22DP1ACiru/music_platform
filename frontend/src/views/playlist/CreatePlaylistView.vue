<script setup lang="ts">
// Only change is the import for usePlaylistStore
import { ref, onUnmounted } from "vue";
import {
  usePlaylistStore, // Updated import path
  type CreatePlaylistPayload,
} from "@/stores/playlist"; // Updated import path
import { useRouter } from "vue-router";

const playlistStore = usePlaylistStore();
const router = useRouter();

const title = ref("");
const description = ref("");
const is_public = ref(true);
const coverArtFile = ref<File | null>(null);
const coverArtPreviewUrl = ref<string | null>(null);

const isLoading = ref(false);
const error = ref<string | null>(null);

const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    if (file.type === "image/gif") {
      alert(
        "Animated GIFs are not allowed. Please use a static image format (JPG, PNG, WEBP)."
      );
      target.value = ""; // Clear the input
      coverArtFile.value = null;
      if (coverArtPreviewUrl.value) {
        URL.revokeObjectURL(coverArtPreviewUrl.value);
        coverArtPreviewUrl.value = null;
      }
      return;
    }
    coverArtFile.value = file;
    if (coverArtPreviewUrl.value) {
      URL.revokeObjectURL(coverArtPreviewUrl.value);
    }
    coverArtPreviewUrl.value = URL.createObjectURL(file);
  } else {
    coverArtFile.value = null;
    if (coverArtPreviewUrl.value) {
      URL.revokeObjectURL(coverArtPreviewUrl.value);
      coverArtPreviewUrl.value = null;
    }
  }
};

const handleSubmit = async () => {
  if (!title.value.trim()) {
    error.value = "Playlist title is required.";
    return;
  }
  isLoading.value = true;
  error.value = null;

  const payload: CreatePlaylistPayload = {
    title: title.value,
    description: description.value,
    is_public: is_public.value,
  };
  if (coverArtFile.value) {
    payload.cover_art = coverArtFile.value;
  }

  const newPlaylist = await playlistStore.createPlaylist(payload);

  isLoading.value = false;
  if (newPlaylist) {
    router.push({ name: "playlist-detail", params: { id: newPlaylist.id } });
  } else {
    error.value =
      playlistStore.error || "Failed to create playlist. Please try again.";
  }
};

onUnmounted(() => {
  if (coverArtPreviewUrl.value) {
    URL.revokeObjectURL(coverArtPreviewUrl.value);
  }
});
</script>

<template>
  <div class="create-playlist-view">
    <h2>Create New Playlist</h2>
    <form @submit.prevent="handleSubmit" class="playlist-form">
      <div class="form-group">
        <label for="playlist-title">Title:</label>
        <input
          type="text"
          id="playlist-title"
          v-model="title"
          required
          maxlength="200"
        />
      </div>
      <div class="form-group">
        <label for="playlist-description">Description (Optional):</label>
        <textarea
          id="playlist-description"
          v-model="description"
          rows="4"
        ></textarea>
      </div>
      <div class="form-group">
        <label for="playlist-cover-art"
          >Cover Art (Optional, JPG/PNG/WEBP):</label
        >
        <div v-if="coverArtPreviewUrl" class="cover-art-preview-container">
          <img
            :src="coverArtPreviewUrl"
            alt="Cover art preview"
            class="cover-art-preview-img"
          />
        </div>
        <input
          type="file"
          id="playlist-cover-art"
          @change="handleCoverArtChange"
          accept="image/jpeg,image/png,image/webp"
        />
      </div>
      <div class="form-group form-group-checkbox">
        <input type="checkbox" id="playlist-public" v-model="is_public" />
        <label for="playlist-public">Make this playlist public?</label>
      </div>

      <div v-if="error" class="error-message">{{ error }}</div>

      <div class="form-actions">
        <button type="submit" :disabled="isLoading">
          {{ isLoading ? "Creating..." : "Create Playlist" }}
        </button>
        <button
          type="button"
          @click="router.back()"
          :disabled="isLoading"
          class="cancel-button"
        >
          Cancel
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.create-playlist-view {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.create-playlist-view h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.playlist-form .form-group {
  margin-bottom: 1rem;
}
.playlist-form label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
}
.playlist-form input[type="text"],
.playlist-form input[type="file"],
.playlist-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.playlist-form input[type="file"] {
  padding: 0.3rem; /* Adjust padding for file input */
}
.playlist-form textarea {
  resize: vertical;
  min-height: 80px;
}

.cover-art-preview-container {
  margin-bottom: 0.5rem;
  width: 150px;
  height: 150px;
  border: 1px dashed var(--color-border-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  border-radius: 4px;
  overflow: hidden;
}
.cover-art-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.form-group-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.form-group-checkbox input[type="checkbox"] {
  width: auto;
  margin-right: 0.3em;
}
.form-group-checkbox label {
  margin-bottom: 0;
  font-weight: normal;
}

.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin: 1rem 0;
  text-align: center;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}
.form-actions button {
  padding: 0.7rem 1.5rem;
}
.cancel-button {
  background-color: var(--color-background-mute);
  border-color: var(--color-border);
  color: var(--color-text);
}
.cancel-button:hover {
  border-color: var(--color-border-hover);
}
</style>
