<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { usePlayerStore } from "@/stores/player";

const playerStore = usePlayerStore();
const audioPlayer = ref<HTMLAudioElement | null>(null); // Ref to the <audio> element

// Watch for changes in the track URL from the store
watch(
  () => playerStore.currentTrackUrl,
  (newUrl) => {
    if (audioPlayer.value && newUrl) {
      console.log("AudioPlayer: Loading new track URL:", newUrl);
      audioPlayer.value.src = newUrl;
      audioPlayer.value.load(); // Important to load the new source
      if (playerStore.isPlaying) {
        // Attempt to play only after user interaction potentially
        audioPlayer.value
          .play()
          .catch((e) => console.warn("Audio autoplay prevented:", e));
      }
    } else if (audioPlayer.value && !newUrl) {
      audioPlayer.value.pause();
      audioPlayer.value.src = ""; // Clear src if no track
    }
  }
);

// Watch for changes in the playing state from the store
watch(
  () => playerStore.isPlaying,
  (newState) => {
    if (!audioPlayer.value) return;
    if (newState && audioPlayer.value.src) {
      console.log("AudioPlayer: Play command received");
      audioPlayer.value
        .play()
        .catch((e) => console.warn("Audio play failed:", e));
    } else {
      console.log("AudioPlayer: Pause command received");
      audioPlayer.value.pause();
    }
  }
);

const handlePlay = () => {
  if (!playerStore.isPlaying) playerStore.resumeTrack(); // Sync store if played externally
};
const handlePause = () => {
  if (playerStore.isPlaying) playerStore.pauseTrack(); // Sync store if paused externally
};
const handleEnded = () => {
  console.log("AudioPlayer: Track ended");
  playerStore.pauseTrack(); // Set state to paused
  // Add logic for next track in queue later
};
// -------------------------------------------

// Note: Autoplay might be blocked by browsers until user interaction.
// The initial play might need to be triggered by the first click.
</script>

<template>
  <div class="audio-player-bar" v-if="playerStore.currentTrackUrl">
    <!-- Only show if a track is loaded -->
    <audio
      ref="audioPlayer"
      @play="handlePlay"
      @pause="handlePause"
      @ended="handleEnded"
      preload="auto"
    >
      Your browser does not support the audio element.
    </audio>

    <div class="player-controls">
      <button @click="playerStore.togglePlayPause()">
        {{ playerStore.isPlaying ? "Pause" : "Play" }}
      </button>
    </div>
    <div class="track-info">
      <span>{{ playerStore.currentTrackDisplayInfo.title }}</span>
      <span class="artist-name">
        - {{ playerStore.currentTrackDisplayInfo.artist }}</span
      >
      <!-- Add Cover Art / Progress Bar / Volume later -->
    </div>
  </div>
</template>

<style scoped>
.audio-player-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 60px; /* Adjust height as needed */
  background-color: var(--color-background-mute);
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  z-index: 1000; /* Keep on top */
  color: var(--color-text);
}
.audio-player-bar-placeholder {
  justify-content: center;
  font-style: italic;
  color: var(--color-text);
}

.player-controls {
  margin-right: 1.5rem;
}
.player-controls button {
  /* Basic styling for play/pause */
  padding: 0.5rem 1rem;
  /* Add icons later */
}

.track-info {
  display: flex;
  flex-direction: column; /* Or row */
  line-height: 1.3;
}
.track-info .artist-name {
  font-size: 0.85em;
  color: var(--color-text);
}
</style>
