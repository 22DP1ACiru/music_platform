<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import type {
  TrackInfoFromApi,
  PlayerTrackInfo,
  Playlist,
  ReleaseDetail,
} from "@/types"; // Assuming PlayerTrackInfo is the target for queue

const props = defineProps<{
  track: TrackInfoFromApi; // The track these actions are for
  // Pass release data if needed to map to PlayerTrackInfo for queue
  releaseData?: ReleaseDetail | Playlist;
}>();

const emit = defineEmits(["addToQueue", "openAddToPlaylistModal"]);

const isDropdownOpen = ref(false);
const dropdownRef = ref<HTMLElement | null>(null);

const toggleDropdown = (event: MouseEvent) => {
  event.stopPropagation(); // Prevent click from immediately closing if bubbling
  isDropdownOpen.value = !isDropdownOpen.value;
};

const handleAddToQueue = () => {
  emit("addToQueue", props.track);
  isDropdownOpen.value = false;
};

const handleOpenAddToPlaylistModal = () => {
  emit("openAddToPlaylistModal", props.track);
  isDropdownOpen.value = false;
};

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isDropdownOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<template>
  <div class="track-actions-container" ref="dropdownRef">
    <button
      @click="toggleDropdown"
      class="actions-trigger-button"
      title="Track Actions"
    >
      ⋮
    </button>
    <div v-if="isDropdownOpen" class="actions-dropdown-menu">
      <button @click="handleAddToQueue" class="dropdown-action-item">
        Add to Queue
      </button>
      <button
        @click="handleOpenAddToPlaylistModal"
        class="dropdown-action-item"
      >
        Add to Playlist
      </button>
    </div>
  </div>
</template>

<style scoped>
.track-actions-container {
  position: relative;
  display: inline-block;
}

.actions-trigger-button {
  background: none;
  border: 1px solid transparent;
  color: var(--color-text-light);
  font-size: 1.2em; /* Adjust for "⋮" or your preferred icon */
  padding: 0.2em 0.5em;
  cursor: pointer;
  border-radius: 4px;
  line-height: 1;
}
.actions-trigger-button:hover {
  color: var(--color-accent);
  background-color: var(--color-background-mute);
}

.actions-dropdown-menu {
  position: absolute;
  top: 100%; /* Position below the button */
  right: 0; /* Align to the right of the button */
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  z-index: 50; /* Ensure it's above other track items */
  min-width: 160px;
  padding: 0.3rem 0;
  margin-top: 0.2rem;
}

.dropdown-action-item {
  display: block;
  width: 100%;
  padding: 0.5rem 0.8rem;
  text-align: left;
  background: none;
  border: none;
  color: var(--color-text);
  font-size: 0.9em;
  cursor: pointer;
}
.dropdown-action-item:hover {
  background-color: var(--color-background-mute);
  color: var(--color-accent);
}
</style>
