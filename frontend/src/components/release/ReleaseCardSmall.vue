<script setup lang="ts">
import type { ReleaseSummary } from "@/types"; // Assuming ReleaseSummary is or will be in types
import { RouterLink } from "vue-router";

defineProps<{
  release: ReleaseSummary;
}>();
</script>

<template>
  <div class="release-card-small">
    <RouterLink
      :to="{ name: 'release-detail', params: { id: release.id } }"
      class="release-link"
    >
      <div class="cover-art-container">
        <img
          v-if="release.cover_art"
          :src="release.cover_art"
          :alt="`${release.title} cover art`"
          class="cover-art"
        />
        <div v-else class="cover-art-placeholder">🎧</div>
      </div>
      <div class="release-info">
        <h4 class="release-title" :title="release.title">
          {{ release.title }}
        </h4>
        <p
          v-if="release.artist"
          class="release-artist"
          :title="release.artist.name"
        >
          {{ release.artist.name }}
        </p>
        <p v-else class="release-artist">Unknown Artist</p>
      </div>
    </RouterLink>
  </div>
</template>

<style scoped>
.release-card-small {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  overflow: hidden; /* Added to ensure nothing spills out of the card itself */
  transition: box-shadow 0.2s ease-in-out, transform 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
}
.release-card-small:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-3px);
}
.release-link {
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  height: 100%;
}
.cover-art-container {
  width: 100%;
  aspect-ratio: 1 / 1; /* Enforces a square aspect ratio for the container */
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden; /* Crucial: clips the parts of the image that are outside the container's bounds */
}
.cover-art {
  width: 100%;
  height: 100%; /* Makes the image try to fill the container */
  object-fit: cover; /* Scales the image to maintain aspect ratio while filling the element’s entire content box. If the image's aspect ratio does not match the aspect ratio of its box, then the object will be clipped to fit. */
}
.cover-art-placeholder {
  font-size: 3rem; /* Adjust size of placeholder icon/text */
  color: var(--color-text-light);
}
.release-info {
  padding: 0.75rem;
  text-align: left;
  flex-grow: 1; /* Allows info to take remaining space if card height is fixed by grid */
}
.release-title {
  font-size: 1em;
  font-weight: 600;
  margin: 0 0 0.25rem 0;
  color: var(--color-heading);
  white-space: nowrap; /* Prevent title from wrapping */
  overflow: hidden; /* Hide overflow */
  text-overflow: ellipsis; /* Add ellipsis for long titles */
}
.release-artist {
  font-size: 0.85em;
  color: var(--color-text);
  margin: 0;
  white-space: nowrap; /* Prevent artist name from wrapping */
  overflow: hidden; /* Hide overflow */
  text-overflow: ellipsis; /* Add ellipsis for long artist names */
}
</style>
