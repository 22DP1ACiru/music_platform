<script setup lang="ts">
import { usePlayerStore } from "@/stores/player";
// No need to import PlayerTrackInfo type here if not explicitly used in script,
// but it's good for clarity if you were, for example, defining local props of that type.

const playerStore = usePlayerStore();

const handlePlayPauseFromQueue = (index: number) => {
  if (index === playerStore.currentQueueIndex) {
    playerStore.togglePlayPause(); // If it's the current track, just toggle its state
  } else {
    playerStore.playTrackFromQueueByIndex(index); // If it's a different track, play it
  }
};

const removeTrack = (index: number) => {
  playerStore.removeTrackFromQueue(index);
};

const formatDuration = (totalSeconds: number | null | undefined): string => {
  if (
    totalSeconds === null ||
    totalSeconds === undefined ||
    !isFinite(totalSeconds) ||
    totalSeconds < 0
  ) {
    return "--:--";
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};

defineEmits(["close"]);
</script>

<template>
  <div class="player-queue-popup">
    <div class="queue-header">
      <h3>Up Next</h3>
      <button @click="$emit('close')" class="close-button" title="Close Queue">
        ×
      </button>
    </div>
    <div class="queue-content">
      <ul v-if="playerStore.queue.length > 0" class="queue-list">
        <li
          v-for="(track, index) in playerStore.queue"
          :key="`${track.id}-${index}`"
          class="queue-item"
          :class="{
            'is-current': index === playerStore.currentQueueIndex,
            'is-playing':
              index === playerStore.currentQueueIndex && playerStore.isPlaying,
            'is-paused':
              index === playerStore.currentQueueIndex &&
              !playerStore.isPlaying &&
              playerStore.currentTrack !== null,
          }"
        >
          <div class="track-art-small">
            <img
              v-if="track.coverArtUrl"
              :src="track.coverArtUrl"
              alt="Cover"
            />
            <div v-else class="placeholder-art"></div>
          </div>
          <div class="track-info">
            <span class="title">{{ track.title }}</span>
            <span class="artist">{{
              track.artistName || "Unknown Artist"
            }}</span>
          </div>
          <span class="duration">{{ formatDuration(track.duration) }}</span>
          <div class="track-actions">
            <button
              @click="handlePlayPauseFromQueue(index)"
              class="action-btn play-btn"
              :title="
                index === playerStore.currentQueueIndex && playerStore.isPlaying
                  ? 'Pause'
                  : 'Play'
              "
            >
              {{
                index === playerStore.currentQueueIndex && playerStore.isPlaying
                  ? "❚❚"
                  : "►"
              }}
            </button>
            <button
              @click="removeTrack(index)"
              class="action-btn remove-btn"
              title="Remove from queue"
            >
              ×
            </button>
          </div>
        </li>
      </ul>
      <p v-else class="empty-queue-message">The queue is empty.</p>
    </div>
    <div class="queue-footer">
      <button
        v-if="playerStore.queue.length > 0"
        @click="playerStore.clearQueue()"
        class="clear-queue-btn"
      >
        Clear Queue
      </button>
    </div>
  </div>
</template>

<style scoped>
.player-queue-popup {
  position: fixed;
  bottom: 70px; /* Height of the audio player bar */
  right: 1rem;
  width: 350px;
  max-height: 50vh; /* Max height before scrolling */
  background-color: var(--c-popup-bg, #eef1f5);
  border: 1px solid var(--c-popup-border, #d1d9e0);
  border-radius: 8px 8px 0 0; /* Rounded top corners */
  box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.1);
  z-index: 1010; /* Above player bar */
  display: flex;
  flex-direction: column;
  color: var(--c-popup-text, #333);
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--c-popup-border, #d1d9e0);
  background-color: var(--c-popup-header-bg, #e4e8ed);
  border-radius: 8px 8px 0 0;
}

.queue-header h3 {
  margin: 0;
  font-size: 1.1em;
  font-weight: 600;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  font-weight: bold;
  color: var(--c-popup-text-light, #666);
  cursor: pointer;
  padding: 0.1em 0.3em;
  line-height: 1;
}
.close-button:hover {
  color: var(--c-popup-text, #333);
}

.queue-content {
  overflow-y: auto;
  flex-grow: 1;
}

.queue-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.queue-item {
  display: flex;
  align-items: center;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid var(--c-popup-item-border, #dde2e7);
  gap: 0.75rem;
  font-size: 0.9em;
}
.queue-item:last-child {
  border-bottom: none;
}

.queue-item.is-current {
  background-color: var(--c-popup-item-current-bg, #d8e0e9);
}
.queue-item.is-playing .title,
.queue-item.is-playing .artist {
  color: var(--c-accent, #007bff);
  font-weight: 600;
}
.queue-item.is-paused .title {
  font-style: italic;
}

.track-art-small {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
}
.track-art-small img,
.track-art-small .placeholder-art {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 3px;
  background-color: var(--c-cover-placeholder-bg, #ccc);
}

.track-info {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
  overflow: hidden;
  line-height: 1.3;
}
.track-info .title,
.track-info .artist {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-info .title {
  font-weight: 500;
}
.track-info .artist {
  font-size: 0.85em;
  color: var(--c-popup-text-light, #555);
}

.duration {
  font-size: 0.85em;
  color: var(--c-popup-text-light, #666);
  margin-left: auto;
  padding-right: 0.5rem;
}

.track-actions {
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.action-btn {
  background: none;
  border: 1px solid transparent;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  padding: 0.2em 0.4em;
  color: var(--c-popup-text-light, #666);
}
.action-btn:hover {
  border-color: var(--c-popup-action-hover-border, #aaa);
  color: var(--c-popup-text, #333);
}
.action-btn.play-btn {
  font-size: 1.1em;
  min-width: 20px;
  text-align: center;
}
.action-btn.remove-btn {
  font-size: 1.2em;
  font-weight: bold;
}
.action-btn.remove-btn:hover {
  color: var(--vt-c-red, #ff3b30);
  border-color: var(--vt-c-red-soft, #ff8f89);
}

.empty-queue-message {
  padding: 2rem 1rem;
  text-align: center;
  font-style: italic;
  color: var(--c-popup-text-light, #777);
}

.queue-footer {
  padding: 0.5rem 1rem;
  text-align: right;
  border-top: 1px solid var(--c-popup-border, #d1d9e0);
}
.clear-queue-btn {
  font-size: 0.85em;
  padding: 0.4em 0.8em;
  background-color: var(--c-popup-button-bg, #dde2e7);
  color: var(--c-popup-button-text, #444);
  border: 1px solid var(--c-popup-button-border, #c5ccd3);
  border-radius: 4px;
  cursor: pointer;
}
.clear-queue-btn:hover {
  background-color: var(--c-popup-button-hover-bg, #c5ccd3);
}
</style>
