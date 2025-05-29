<script setup lang="ts">
// Only change is the import for usePlaylistStore
import { onMounted, computed } from "vue";
import { usePlaylistStore } from "@/stores/playlist"; // Updated import path
import { useAuthStore } from "@/stores/auth";
import { RouterLink, useRouter } from "vue-router";
import PlaylistCard from "@/components/playlist/PlaylistCard.vue"; // Updated import path

const playlistStore = usePlaylistStore();
const authStore = useAuthStore();
const router = useRouter();

const myPlaylists = computed(() => playlistStore.myPlaylists);
const isLoading = computed(() => playlistStore.isLoadingMyPlaylists);
const error = computed(() => playlistStore.error);

onMounted(() => {
  if (authStore.isLoggedIn) {
    playlistStore.fetchMyPlaylists();
  } else {
    // Redirect to login if not authenticated
    router.push({ name: "login", query: { redirect: "/playlists/my" } });
  }
});
</script>

<template>
  <div class="my-playlists-view">
    <div class="header-actions">
      <h2>My Playlists</h2>
      <RouterLink :to="{ name: 'playlist-create' }" class="create-playlist-btn"
        >+ Create Playlist</RouterLink
      >
    </div>

    <div v-if="isLoading" class="loading-message">
      Loading your playlists...
    </div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div
      v-else-if="!myPlaylists || myPlaylists.length === 0"
      class="empty-state"
    >
      <p>You haven't created any playlists yet.</p>
    </div>

    <div v-else class="playlists-grid">
      <PlaylistCard
        v-for="playlist in myPlaylists"
        :key="playlist.id"
        :playlist="playlist"
      />
    </div>
  </div>
</template>

<style scoped>
.my-playlists-view {
  max-width: 1000px;
  margin: 2rem auto;
  padding: 1rem;
}
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.my-playlists-view h2 {
  color: var(--color-heading);
  margin: 0;
}
.create-playlist-btn {
  background-color: var(--color-accent);
  color: white;
  padding: 0.6em 1.2em;
  border-radius: 5px;
  text-decoration: none;
  font-size: 0.95em;
  font-weight: 500;
}
.create-playlist-btn:hover {
  background-color: var(--color-accent-hover);
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

.playlists-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
}
</style>
