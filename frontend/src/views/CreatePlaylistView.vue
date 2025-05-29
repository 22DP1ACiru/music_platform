<script setup lang="ts">
import { ref } from "vue";
import { usePlaylistStore } from "@/stores/playlistStore";
import { useRouter } from "vue-router";

const playlistStore = usePlaylistStore();
const router = useRouter();

const title = ref("");
const description = ref("");
const is_public = ref(true); // Default to public

const isLoading = ref(false);
const error = ref<string | null>(null);

const handleSubmit = async () => {
  if (!title.value.trim()) {
    error.value = "Playlist title is required.";
    return;
  }
  isLoading.value = true;
  error.value = null;

  const newPlaylist = await playlistStore.createPlaylist({
    title: title.value,
    description: description.value,
    is_public: is_public.value,
  });

  isLoading.value = false;
  if (newPlaylist) {
    // Navigate to the detail page of the newly created playlist
    router.push({ name: "playlist-detail", params: { id: newPlaylist.id } });
  } else {
    error.value =
      playlistStore.error || "Failed to create playlist. Please try again.";
  }
};
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
.playlist-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.playlist-form textarea {
  resize: vertical;
  min-height: 80px;
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
