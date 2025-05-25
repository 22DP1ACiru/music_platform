<script setup lang="ts">
import { ref, watch, onMounted, computed, nextTick, onUnmounted } from "vue";
import { usePlayerStore } from "@/stores/player";
import PlayerQueue from "./PlayerQueue.vue";

const playerStore = usePlayerStore();
const audioPlayer = ref<HTMLAudioElement | null>(null);
const isSeeking = ref(false); // True when user is dragging the progress bar
const userHasInteracted = ref(false);
const showQueuePopup = ref(false);

const titleContainerRef = ref<HTMLElement | null>(null);
const titleTextRef = ref<HTMLElement | null>(null);
const artistContainerRef = ref<HTMLElement | null>(null);
const artistTextRef = ref<HTMLElement | null>(null);

const isTitleOverflowing = ref(false);
const isArtistOverflowing = ref(false);

const formattedCurrentTime = computed(() =>
  formatTime(playerStore.currentTime)
);
const formattedDuration = computed(() => formatTime(playerStore.duration));

function formatTime(secs: number): string {
  if (isNaN(secs) || !isFinite(secs) || secs < 0) return "0:00";
  const minutes = Math.floor(secs / 60);
  const seconds = Math.floor(secs % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

const checkTextOverflow = () => {
  nextTick(() => {
    if (titleContainerRef.value && titleTextRef.value) {
      isTitleOverflowing.value =
        titleTextRef.value.scrollWidth > titleContainerRef.value.clientWidth;
    } else {
      isTitleOverflowing.value = false;
    }
    if (artistContainerRef.value && artistTextRef.value) {
      isArtistOverflowing.value =
        artistTextRef.value.scrollWidth > artistContainerRef.value.clientWidth;
    } else {
      isArtistOverflowing.value = false;
    }
  });
};

const tryToPlayAudio = () => {
  if (!audioPlayer.value || !audioPlayer.value.src) {
    console.log(
      "AudioPlayer: tryToPlayAudio - Aborted: No audio element or src."
    );
    return;
  }

  if (playerStore.isPlaying && audioPlayer.value.paused) {
    if (audioPlayer.value.readyState >= 3) {
      // HAVE_FUTURE_DATA or more
      console.log(
        `AudioPlayer: tryToPlayAudio - Player ready (state ${audioPlayer.value.readyState}). Attempting play().`
      );
      const playPromise = audioPlayer.value.play();
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          console.warn("AudioPlayer: tryToPlayAudio - Playback failed:", error);
        });
      }
    } else {
      console.log(
        `AudioPlayer: tryToPlayAudio - Player not ready enough (state ${audioPlayer.value.readyState}). Play will be attempted on 'canplay' or other readiness events.`
      );
      // It might be beneficial to call audioPlayer.value.load() here if src is set but not ready,
      // though the src watcher usually handles load().
    }
  } else if (!playerStore.isPlaying && !audioPlayer.value.paused) {
    console.log(
      "AudioPlayer: tryToPlayAudio - Store wants pause, player is playing. Pausing."
    );
    audioPlayer.value.pause();
  }
};

const onLoadedMetadata = () => {
  if (audioPlayer.value) {
    playerStore.setDuration(audioPlayer.value.duration);
    checkTextOverflow(); // Check overflow after metadata, track info is now definite
  }
};

const onCanPlay = () => {
  if (audioPlayer.value) {
    console.log(
      "AudioPlayer: CanPlay event. ReadyState:",
      audioPlayer.value.readyState
    );
    tryToPlayAudio(); // Attempt to play if store says it should be playing
  }
};

const onTimeUpdate = () => {
  if (audioPlayer.value && !isSeeking.value) {
    // Only update store if user is not actively dragging the progress bar
    playerStore.setCurrentTime(audioPlayer.value.currentTime);
  }
};

const onVolumeChange = () => {
  if (audioPlayer.value) {
    if (playerStore.volume !== audioPlayer.value.volume) {
      playerStore.setVolume(audioPlayer.value.volume);
    }
    if (playerStore.isMuted !== audioPlayer.value.muted) {
      playerStore.setMuted(audioPlayer.value.muted);
    }
  }
};

const onEnded = () => {
  playerStore.handleTrackEnd();
};

// --- Watchers ---

watch(
  () => playerStore.currentTrackUrl,
  (newUrl, oldUrl) => {
    if (audioPlayer.value && newUrl) {
      // Only change src and load if the URL is actually different
      if (newUrl !== audioPlayer.value.src) {
        console.log(
          `AudioPlayer: currentTrackUrl changed. New: ${newUrl}. Loading.`
        );
        audioPlayer.value.src = newUrl;
        playerStore.resetTimes(); // Reset store times for the new track
        audioPlayer.value.load(); // Important to load the new source
      } else if (
        playerStore.isPlaying &&
        audioPlayer.value.paused &&
        newUrl === oldUrl
      ) {
        // This handles "repeat one" or if store state changes to play for the *same* track
        console.log(
          "AudioPlayer: currentTrackUrl same, but store wants play (e.g., repeat one)."
        );
        tryToPlayAudio();
      }
    } else if (audioPlayer.value && !newUrl) {
      console.log(
        "AudioPlayer: currentTrackUrl cleared. Pausing and resetting src."
      );
      audioPlayer.value.pause();
      audioPlayer.value.src = "";
      playerStore.resetTimes();
    }
    checkTextOverflow(); // Check overflow when track potentially changes
  },
  { flush: "post" } // Ensure DOM updates before watcher logic if needed for src
);

watch(
  () => playerStore.isPlaying,
  (shouldPlay) => {
    // `shouldPlay` is the new value of playerStore.isPlaying
    if (!audioPlayer.value) return;
    console.log(
      `AudioPlayer: isPlaying watcher. Store wants play: ${shouldPlay}. Player currently paused: ${audioPlayer.value.paused}.`
    );
    // Using nextTick to allow other state changes (like src or currentTime from another watcher) to settle
    nextTick(() => {
      tryToPlayAudio();
    });
  }
);

// Watch for programmatic changes to currentTime from the store (e.g., replay, seek via store)
watch(
  () => playerStore.currentTime,
  (newStoreTime) => {
    if (audioPlayer.value && !isSeeking.value) {
      // If the audio element's time is significantly different from the store's time, update it.
      // This handles cases where the store dictates a new time (e.g., replay from 0).
      // A small threshold (e.g., 0.5s) prevents fighting over minor discrepancies from timeupdate events.
      const delta = Math.abs(audioPlayer.value.currentTime - newStoreTime);
      if (delta > 0.5) {
        console.log(
          `AudioPlayer: Store currentTime changed to ${newStoreTime}. Audio element currentTime is ${audioPlayer.value.currentTime}. Seeking audio element.`
        );
        audioPlayer.value.currentTime = newStoreTime;
      }
    }
  }
);

watch(
  () => playerStore.volume,
  (newVolume) => {
    if (audioPlayer.value && audioPlayer.value.volume !== newVolume) {
      audioPlayer.value.volume = newVolume;
    }
  }
);

watch(
  () => playerStore.isMuted,
  (newMuteState) => {
    if (audioPlayer.value && audioPlayer.value.muted !== newMuteState) {
      audioPlayer.value.muted = newMuteState;
    }
  }
);

watch(
  () => playerStore.currentTrackDisplayInfo,
  () => {
    checkTextOverflow();
  },
  { deep: true, immediate: true } // immediate true to check on initial load
);

const handleProgressSeek = (event: Event) => {
  if (audioPlayer.value && playerStore.duration > 0) {
    const target = event.target as HTMLInputElement;
    const newTime = parseFloat(target.value);
    // Set the audio element's time directly first for responsiveness
    audioPlayer.value.currentTime = newTime;
    // Then update the store. The store watcher for currentTime won't fight back
    // because `isSeeking` will be true (or delta won't be large enough if mousedown/up is quick).
    playerStore.setCurrentTime(newTime);
  }
};
const onSeekMouseDown = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  isSeeking.value = true;
};
const onSeekMouseUp = () => {
  isSeeking.value = false;
  // After user finishes seeking, if the store indicates it should be playing, ensure it is.
  // This is because a mousedown might pause playback if browser policies are strict.
  if (playerStore.isPlaying && audioPlayer.value?.paused) {
    tryToPlayAudio();
  }
};

const handleTogglePlayPauseClick = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  playerStore.togglePlayPause();
};

const handleVolumeSeek = (event: Event) => {
  if (audioPlayer.value) {
    if (!userHasInteracted.value) userHasInteracted.value = true;
    const target = event.target as HTMLInputElement;
    const newVolume = parseFloat(target.value);
    playerStore.setVolume(newVolume); // This will trigger the volume watcher
    if (newVolume > 0 && playerStore.isMuted) {
      playerStore.setMuted(false); // Unmute if volume is turned up
    }
  }
};

const toggleQueuePopup = () => {
  showQueuePopup.value = !showQueuePopup.value;
};

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  if (audioPlayer.value) {
    audioPlayer.value.volume = playerStore.volume;
    audioPlayer.value.muted = playerStore.isMuted;

    // If store has a track on mount, set it up.
    if (playerStore.currentTrackUrl) {
      const currentAudioSrc = audioPlayer.value.src.endsWith(
        playerStore.currentTrackUrl
      )
        ? playerStore.currentTrackUrl
        : audioPlayer.value.src; // Handle full URL vs relative

      if (currentAudioSrc !== playerStore.currentTrackUrl) {
        console.log(
          "AudioPlayer: onMounted - Setting initial src from store:",
          playerStore.currentTrackUrl
        );
        audioPlayer.value.src = playerStore.currentTrackUrl;
        // If src was set, and store indicates it should be playing, tryToPlayAudio will be called by isPlaying watcher
        // or by canplay event. For robustness, explicit load if src was empty:
        if (!currentAudioSrc) {
          // if audioPlayer.value.src was initially ""
          audioPlayer.value.load();
        }
      }
      // If store has a specific currentTime (e.g. persisted session), set it
      if (
        playerStore.currentTime > 0 &&
        playerStore.currentTime < playerStore.duration
      ) {
        audioPlayer.value.currentTime = playerStore.currentTime;
      }
    }
  }
  checkTextOverflow();

  // Setup ResizeObserver for marquee effect
  if (titleContainerRef.value && artistContainerRef.value) {
    resizeObserver = new ResizeObserver(checkTextOverflow);
    if (titleContainerRef.value)
      resizeObserver.observe(titleContainerRef.value);
    if (artistContainerRef.value)
      resizeObserver.observe(artistContainerRef.value);
  }
});

onUnmounted(() => {
  if (resizeObserver) {
    if (titleContainerRef.value)
      resizeObserver.unobserve(titleContainerRef.value);
    if (artistContainerRef.value)
      resizeObserver.unobserve(artistContainerRef.value);
    resizeObserver.disconnect();
  }
});

const repeatModeIcon = computed(() => {
  switch (playerStore.repeatMode) {
    case "one":
      return "🔂";
    case "all":
      return "🔁";
    default:
      return "➡️";
  }
});

const queueButtonIcon = computed(() => {
  return showQueuePopup.value ? "✕" : "☰";
});
</script>

<template>
  <div
    class="audio-player-bar"
    v-if="playerStore.currentTrack || playerStore.queue.length > 0"
  >
    <audio
      ref="audioPlayer"
      @loadedmetadata="onLoadedMetadata"
      @canplay="onCanPlay"
      @timeupdate="onTimeUpdate"
      @volumechange="onVolumeChange"
      @ended="onEnded"
      @error="(e) => console.error('Audio Element Error:', (e.target as HTMLAudioElement).error?.code, (e.target as HTMLAudioElement).error?.message)"
      preload="metadata"
    >
      Your browser does not support the audio element.
    </audio>
    <!-- Comment moved outside or removed if not needed for clarity during dev -->
    <!-- preload="metadata" helps get duration faster. -->

    <PlayerQueue v-if="showQueuePopup" @close="showQueuePopup = false" />

    <div class="player-content">
      <div class="track-art-info">
        <img
          v-if="playerStore.currentTrackCoverArtUrl"
          :src="playerStore.currentTrackCoverArtUrl"
          alt="Cover Art"
          class="cover-art-small"
        />
        <div v-else class="cover-art-small placeholder"></div>
        <div class="track-details">
          <div
            class="title-container"
            ref="titleContainerRef"
            :class="{ marquee: isTitleOverflowing }"
          >
            <span class="title-text" ref="titleTextRef">{{
              playerStore.currentTrackDisplayInfo.title
            }}</span>
          </div>
          <div
            class="artist-container"
            ref="artistContainerRef"
            :class="{ marquee: isArtistOverflowing }"
          >
            <span class="artist-text" ref="artistTextRef">{{
              playerStore.currentTrackDisplayInfo.artist
            }}</span>
          </div>
        </div>
      </div>

      <div class="player-controls-main">
        <button
          @click="playerStore.playPreviousInQueue()"
          title="Previous"
          :disabled="
            playerStore.queue.length === 0 && !playerStore.currentTrack
          "
        >
          ⏮
        </button>
        <button
          @click="handleTogglePlayPauseClick"
          class="play-pause-btn"
          :title="playerStore.isPlaying ? 'Pause' : 'Play'"
          :disabled="!playerStore.currentTrack"
        >
          {{ playerStore.isPlaying ? "❚❚" : "►" }}
        </button>
        <button
          @click="playerStore.playNextInQueue()"
          title="Next"
          :disabled="
            playerStore.queue.length === 0 && !playerStore.currentTrack
          "
        >
          ⏭
        </button>
      </div>

      <div class="progress-section">
        <span class="time-display current-time">{{
          formattedCurrentTime
        }}</span>
        <input
          type="range"
          class="progress-bar"
          :value="playerStore.currentTime"
          :max="playerStore.duration || 0"
          step="0.1"
          @input="handleProgressSeek"
          @change="handleProgressSeek"
          @mousedown="onSeekMouseDown"
          @mouseup="onSeekMouseUp"
          :disabled="!playerStore.duration || playerStore.duration === 0"
        />
        <span class="time-display total-time">{{ formattedDuration }}</span>
      </div>

      <div class="player-controls-side">
        <button
          @click="playerStore.toggleMute()"
          :title="playerStore.isMuted ? 'Unmute' : 'Mute'"
        >
          {{ playerStore.isMuted ? "🔇" : "🔊" }}
        </button>
        <input
          type="range"
          class="volume-slider"
          min="0"
          max="1"
          step="0.01"
          :value="playerStore.volume"
          @input="handleVolumeSeek"
          :disabled="playerStore.isMuted"
        />
        <button
          @click="playerStore.cycleRepeatMode()"
          :title="`Repeat: ${playerStore.repeatMode}`"
          class="repeat-button"
        >
          {{ repeatModeIcon }}
        </button>
        <button
          @click="toggleQueuePopup"
          :title="showQueuePopup ? 'Hide Queue' : 'Show Queue'"
          class="queue-toggle-button"
          :class="{ active: showQueuePopup }"
        >
          {{ queueButtonIcon }}
        </button>
      </div>
    </div>
  </div>
  <div v-else class="audio-player-bar audio-player-bar-placeholder">
    <span>No track selected.</span>
  </div>
</template>

<style scoped>
.audio-player-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 70px;
  background-color: var(--c-player-bg, #f3f3f3);
  border-top: 1px solid var(--c-player-border, #e0e0e0);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  z-index: 1000;
  color: var(--c-player-text, #333);
}

.audio-player-bar-placeholder {
  justify-content: center;
  font-style: italic;
}

.player-content {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 1rem;
}

.track-art-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 220px;
  min-width: 180px;
  flex-shrink: 0;
}

.cover-art-small {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--c-cover-placeholder-bg, #ccc);
  flex-shrink: 0;
}
.cover-art-small.placeholder {
  border: 1px dashed var(--c-cover-placeholder-border, #aaa);
}

.track-details {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
  overflow: hidden;
  width: 100%;
}

.title-container,
.artist-container {
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
}

.title-text,
.artist-text {
  display: inline-block;
  white-space: nowrap;
}
.track-details .title-text {
  font-weight: 500;
  color: var(--c-player-title, #000);
}
.track-details .artist-text {
  font-size: 0.85em;
  color: var(--c-player-artist, #555);
}

.marquee .title-text,
.marquee .artist-text {
  animation: marquee-scroll 10s linear infinite;
  padding-left: 100%;
  will-change: transform;
}

@keyframes marquee-scroll {
  0% {
    transform: translateX(0%);
  }
  100% {
    transform: translateX(-100%);
  }
}

.marquee:hover .title-text,
.marquee:hover .artist-text {
  animation-play-state: paused;
}

.player-controls-main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.player-controls-main button {
  background: none;
  border: none;
  color: var(--c-player-controls-main-icon, #444);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.3em;
}
.player-controls-main button:hover:not(:disabled) {
  color: var(--c-player-controls-main-icon-hover, #007bff);
}
.player-controls-main button:disabled {
  color: var(--c-player-controls-disabled, #aaa);
  cursor: not-allowed;
}

.play-pause-btn {
  font-size: 1.8rem !important;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
}
.play-pause-btn:hover:not(:disabled) {
  background-color: var(--c-playbtn-hover-bg, #e9e9e9);
}

.progress-section {
  flex-grow: 1;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 150px;
}

.progress-bar {
  flex-grow: 1;
  height: 8px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--c-progress-track-bg, #ddd);
  border-radius: 4px;
  cursor: pointer;
  outline: none;
}
.progress-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  background: var(--c-progress-thumb-bg, #007bff);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid var(--c-progress-thumb-border, #fff);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
}
.progress-bar::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: var(--c-progress-thumb-bg, #007bff);
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid var(--c-progress-thumb-border, #fff);
  box-shadow: 0 0 2px rgba(0, 0, 0, 0.2);
}
.progress-bar:disabled::-webkit-slider-thumb {
  background: var(--c-progress-thumb-disabled-bg, #999);
  border-color: var(--c-progress-thumb-disabled-border, #ccc);
  cursor: not-allowed;
}
.progress-bar:disabled::-moz-range-thumb {
  background: var(--c-progress-thumb-disabled-bg, #999);
  border-color: var(--c-progress-thumb-disabled-border, #ccc);
  cursor: not-allowed;
}
.progress-bar:disabled {
  cursor: not-allowed;
}

.time-display {
  font-size: 0.85em;
  min-width: 35px;
  text-align: center;
  color: var(--c-player-time, #333);
}

.player-controls-side {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.player-controls-side button {
  background: none;
  border: none;
  color: var(--c-player-controls-side-icon, #444);
  font-size: 1.1rem;
  cursor: pointer;
  padding: 0.3em;
  min-width: 28px;
  text-align: center;
}
.player-controls-side button:hover {
  color: var(--c-player-controls-side-icon-hover, #007bff);
}
.repeat-button,
.queue-toggle-button {
  min-width: 2em;
  text-align: center;
}
.queue-toggle-button.active {
  color: var(--c-player-controls-side-icon-hover, #007bff);
}

.volume-slider {
  width: 80px;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: var(--c-volume-track-bg, #ddd);
  border-radius: 3px;
  cursor: pointer;
  outline: none;
}
.volume-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 14px;
  height: 14px;
  background: var(--c-volume-thumb-bg, #555);
  border-radius: 50%;
  border: 1px solid var(--c-volume-thumb-border, #fff);
}
.volume-slider::-moz-range-thumb {
  width: 14px;
  height: 14px;
  background: var(--c-volume-thumb-bg, #555);
  border-radius: 50%;
  border: 1px solid var(--c-volume-thumb-border, #fff);
}
.volume-slider:disabled::-webkit-slider-thumb {
  background: var(--c-volume-thumb-disabled-bg, #999);
  cursor: not-allowed;
}
.volume-slider:disabled::-moz-range-thumb {
  background: var(--c-volume-thumb-disabled-bg, #999);
  cursor: not-allowed;
}
.volume-slider:disabled {
  cursor: not-allowed;
}
</style>
