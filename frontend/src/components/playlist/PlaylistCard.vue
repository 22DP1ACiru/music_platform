<script setup lang="ts">
import type { Playlist } from "@/types";
import { RouterLink } from "vue-router";

defineProps<{
  playlist: Playlist;
}>();
</script>

<template>
  <div class="playlist-card">
    <RouterLink
      :to="{ name: 'playlist-detail', params: { id: playlist.id } }"
      class="playlist-link"
    >
      <div class="playlist-cover-art-container">
        <img
          v-if="playlist.cover_art"
          :src="playlist.cover_art"
          alt="Playlist cover"
          class="playlist-cover-art"
        />
        <div v-else class="playlist-cover-art-placeholder">🎵</div>
      </div>
      <div class="playlist-info">
        <h3 class="playlist-title">{{ playlist.title }}</h3>
        <p class="playlist-meta">
          {{ playlist.track_count }} track{{
            playlist.track_count !== 1 ? "s" : ""
          }}
          <span v-if="!playlist.is_public" class="private-badge">Private</span>
        </p>
      </div>
    </RouterLink>
  </div>
</template>

<style scoped>
.playlist-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  transition: box-shadow 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
}
.playlist-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.playlist-link {
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.playlist-cover-art-container {
  width: 100%;
  aspect-ratio: 1 / 1;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
}
.playlist-cover-art {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.playlist-cover-art-placeholder {
  font-size: 3rem;
  color: var(--color-text-light);
}
.playlist-info {
  padding: 0.8rem 1rem;
  text-align: left;
  flex-grow: 1;
}
.playlist-title {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0 0 0.3rem 0;
  color: var(--color-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.playlist-meta {
  font-size: 0.85em;
  color: var(--color-text-light);
  margin: 0;
}
.private-badge {
  margin-left: 0.5em;
  background-color: var(--color-background-mute);
  color: var(--color-text);
  padding: 0.1em 0.4em;
  border-radius: 3px;
  font-size: 0.9em;
}
</style>
