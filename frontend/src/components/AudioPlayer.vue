<script setup lang="ts">
import { ref, watch, onMounted, computed, nextTick, onUnmounted } from "vue";
import { usePlayerStore } from "@/stores/player";
import PlayerQueue from "./PlayerQueue.vue";

const playerStore = usePlayerStore();
const audioPlayer = ref<HTMLAudioElement | null>(null);
const isSeeking = ref(false);
const userHasInteracted = ref(false);
const showQueuePopup = ref(false);

const titleContainerRef = ref<HTMLElement | null>(null);
const titleTextContentRef = ref<HTMLElement | null>(null); // Refers to the span with actual text
const artistContainerRef = ref<HTMLElement | null>(null);
const artistTextContentRef = ref<HTMLElement | null>(null);

const isTitleOverflowing = ref(false);
const isArtistOverflowing = ref(false);

const titleAnimationProps = ref({ duration: "10s", scrollAmountToEnd: "0px" });
const artistAnimationProps = ref({ duration: "8s", scrollAmountToEnd: "0px" });

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
  // Reset overflow flags first
  isTitleOverflowing.value = false;
  isArtistOverflowing.value = false;

  nextTick(() => {
    // Wait for DOM to update with new text
    if (titleContainerRef.value && titleTextContentRef.value) {
      const containerWidth = titleContainerRef.value.clientWidth;
      const textWidth = titleTextContentRef.value.scrollWidth;

      if (textWidth > containerWidth) {
        isTitleOverflowing.value = true;
        const scrollDistance = textWidth - containerWidth; // How much to move left to show the end
        const scrollSpeed = 40; // pixels per second, adjust as needed
        const scrollPhaseDuration = Math.max(2, scrollDistance / scrollSpeed); // Min 2s for scroll phase
        const pausePhaseDuration = 2; // 2s pause at start and end

        titleAnimationProps.value.duration = `${
          pausePhaseDuration * 2 + scrollPhaseDuration * 2
        }s`;
        titleAnimationProps.value.scrollAmountToEnd = `-${scrollDistance}px`;
      }
    }

    if (artistContainerRef.value && artistTextContentRef.value) {
      const containerWidth = artistContainerRef.value.clientWidth;
      const textWidth = artistTextContentRef.value.scrollWidth;

      if (textWidth > containerWidth) {
        isArtistOverflowing.value = true;
        const scrollDistance = textWidth - containerWidth;
        const scrollSpeed = 35;
        const scrollPhaseDuration = Math.max(1.5, scrollDistance / scrollSpeed);
        const pausePhaseDuration = 2;

        artistAnimationProps.value.duration = `${
          pausePhaseDuration * 2 + scrollPhaseDuration * 2
        }s`;
        artistAnimationProps.value.scrollAmountToEnd = `-${scrollDistance}px`;
      }
    }
  });
};

const tryToPlayAudio = () => {
  if (!audioPlayer.value || !audioPlayer.value.src) return;
  if (playerStore.isPlaying && audioPlayer.value.paused) {
    if (audioPlayer.value.readyState >= 3) {
      audioPlayer.value.play().catch((e) => console.warn("Play failed:", e));
    }
  } else if (!playerStore.isPlaying && !audioPlayer.value.paused) {
    audioPlayer.value.pause();
  }
};

const onLoadedMetadata = () => {
  if (audioPlayer.value) playerStore.setDuration(audioPlayer.value.duration);
  checkTextOverflow();
};
const onCanPlay = () => {
  if (audioPlayer.value) tryToPlayAudio();
};
const onTimeUpdate = () => {
  if (audioPlayer.value && !isSeeking.value)
    playerStore.setCurrentTime(audioPlayer.value.currentTime);
};
const onVolumeChange = () => {
  if (audioPlayer.value) {
    if (playerStore.volume !== audioPlayer.value.volume)
      playerStore.setVolume(audioPlayer.value.volume);
    if (playerStore.isMuted !== audioPlayer.value.muted)
      playerStore.setMuted(audioPlayer.value.muted);
  }
};
const onEnded = () => playerStore.handleTrackEnd();

watch(
  () => playerStore.currentTrackUrl,
  (newUrl) => {
    // Reset overflow flags immediately when track URL changes, before new text is measured
    isTitleOverflowing.value = false;
    isArtistOverflowing.value = false;

    if (audioPlayer.value && newUrl) {
      if (newUrl !== audioPlayer.value.src) {
        audioPlayer.value.src = newUrl;
        playerStore.resetTimes();
        audioPlayer.value.load();
      } else if (playerStore.isPlaying && audioPlayer.value.paused) {
        tryToPlayAudio();
      }
    } else if (audioPlayer.value && !newUrl) {
      audioPlayer.value.pause();
      audioPlayer.value.src = "";
      playerStore.resetTimes();
    }
    // `checkTextOverflow` will be called by currentTrackDisplayInfo watcher or onLoadedMetadata
  },
  { flush: "post" }
);

watch(
  () => playerStore.isPlaying,
  () => {
    if (!audioPlayer.value) return;
    nextTick(tryToPlayAudio);
  }
);

watch(
  () => playerStore.currentTime,
  (newStoreTime) => {
    if (audioPlayer.value && !isSeeking.value) {
      const delta = Math.abs(audioPlayer.value.currentTime - newStoreTime);
      if (delta > 0.5) audioPlayer.value.currentTime = newStoreTime;
    }
  }
);

watch(
  () => playerStore.volume,
  (newVolume) => {
    if (audioPlayer.value && audioPlayer.value.volume !== newVolume)
      audioPlayer.value.volume = newVolume;
  }
);
watch(
  () => playerStore.isMuted,
  (newMuteState) => {
    if (audioPlayer.value && audioPlayer.value.muted !== newMuteState)
      audioPlayer.value.muted = newMuteState;
  }
);

watch(
  () => playerStore.currentTrackDisplayInfo,
  () => {
    // When display info changes (new track), explicitly call checkTextOverflow
    // This ensures it runs *after* Vue has updated the DOM with the new text
    checkTextOverflow();
  },
  { deep: true, immediate: true } // immediate true to check on initial load
);

const handleProgressSeek = (event: Event) => {
  if (audioPlayer.value && playerStore.duration > 0) {
    const newTime = parseFloat((event.target as HTMLInputElement).value);
    audioPlayer.value.currentTime = newTime;
    playerStore.setCurrentTime(newTime);
  }
};
const onSeekMouseDown = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  isSeeking.value = true;
};
const onSeekMouseUp = () => {
  isSeeking.value = false;
  if (playerStore.isPlaying && audioPlayer.value?.paused) tryToPlayAudio();
};
const handleTogglePlayPauseClick = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  playerStore.togglePlayPause();
};
const handleVolumeSeek = (event: Event) => {
  if (audioPlayer.value) {
    if (!userHasInteracted.value) userHasInteracted.value = true;
    const newVolume = parseFloat((event.target as HTMLInputElement).value);
    playerStore.setVolume(newVolume);
    if (newVolume > 0 && playerStore.isMuted) playerStore.setMuted(false);
  }
};
const toggleQueuePopup = () => (showQueuePopup.value = !showQueuePopup.value);

let resizeObserver: ResizeObserver | null = null;
onMounted(() => {
  if (audioPlayer.value) {
    audioPlayer.value.volume = playerStore.volume;
    audioPlayer.value.muted = playerStore.isMuted;
    if (playerStore.currentTrackUrl) {
      const currentAudioSrc = audioPlayer.value.src.endsWith(
        playerStore.currentTrackUrl
      )
        ? playerStore.currentTrackUrl
        : audioPlayer.value.src;
      if (currentAudioSrc !== playerStore.currentTrackUrl) {
        audioPlayer.value.src = playerStore.currentTrackUrl;
        if (!currentAudioSrc) audioPlayer.value.load();
      }
      if (
        playerStore.currentTime > 0 &&
        playerStore.currentTime < playerStore.duration
      ) {
        audioPlayer.value.currentTime = playerStore.currentTime;
      }
    }
  }

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

const repeatModeIcon = computed(() =>
  playerStore.repeatMode === "one"
    ? "🔂"
    : playerStore.repeatMode === "all"
    ? "🔁"
    : "➡️"
);
const queueButtonIcon = computed(() => (showQueuePopup.value ? "✕" : "☰"));
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
          <div class="title-container" ref="titleContainerRef">
            <span
              class="text-animate-wrapper"
              :class="{ 'marquee-spotify-refined': isTitleOverflowing }"
              :style="{
                '--animation-duration': titleAnimationProps.duration,
                '--text-scroll-amount-to-end':
                  titleAnimationProps.scrollAmountToEnd,
              }"
            >
              <span
                class="text-content"
                ref="titleTextContentRef"
                :key="playerStore.currentTrackDisplayInfo.title + '-title'"
              >
                {{ playerStore.currentTrackDisplayInfo.title }}
              </span>
            </span>
          </div>
          <div class="artist-container" ref="artistContainerRef">
            <span
              class="text-animate-wrapper"
              :class="{ 'marquee-spotify-refined': isArtistOverflowing }"
              :style="{
                '--animation-duration': artistAnimationProps.duration,
                '--text-scroll-amount-to-end':
                  artistAnimationProps.scrollAmountToEnd,
              }"
            >
              <span
                class="text-content"
                ref="artistTextContentRef"
                :key="playerStore.currentTrackDisplayInfo.artist + '-artist'"
              >
                {{ playerStore.currentTrackDisplayInfo.artist }}
              </span>
            </span>
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

.text-animate-wrapper {
  /* This wrapper will be animated */
  display: inline-block; /* So its width is the text width, allowing transform to work as expected */
  white-space: nowrap;
  /* transform: translateZ(0); /* Potential Chrome fix: promote to its own layer */
}

.text-animate-wrapper.marquee-spotify-refined {
  animation-name: spotify-scroll-refined;
  animation-timing-function: linear; /* Linear for smooth scroll phases */
  animation-iteration-count: infinite;
  animation-duration: var(--animation-duration, 10s); /* Controlled by JS */
  will-change: transform;
}

.text-animate-wrapper.marquee-spotify-refined:hover {
  animation-play-state: paused;
}

.text-content {
  /* The actual text lives here */
  display: inline-block; /* Helps with width calculation */
}

.title-container .text-content {
  font-weight: 500;
  color: var(--c-player-title, #000);
}
.artist-container .text-content {
  font-size: 0.85em;
  color: var(--c-player-artist, #555);
}

/* Keyframes for Spotify-like scroll: Pause -> Scroll Left -> Pause -> Scroll Right */
@keyframes spotify-scroll-refined {
  0% {
    transform: translateX(0);
  } /* Initial position, start of first pause */
  20% {
    transform: translateX(0);
  } /* End of first pause (20% of duration) */

  /* Start scrolling left until the end of the text is visible */
  /* The translateX value is --text-scroll-amount-to-end (negative) */
  70% {
    transform: translateX(var(--text-scroll-amount-to-end));
  } /* End of scroll left, start of second pause (50% duration for scroll) */
  90% {
    transform: translateX(var(--text-scroll-amount-to-end));
  } /* End of second pause (20% duration for pause) */

  100% {
    transform: translateX(0);
  } /* Scroll back to start (10% duration for scroll back) */
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
