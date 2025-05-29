<script setup lang="ts">
import { ref, watch, onMounted, computed, nextTick, onUnmounted } from "vue";
import { usePlayerStore } from "@/stores/player";
import PlayerQueue from "@/components/player/PlayerQueue.vue"; // Updated import path

const playerStore = usePlayerStore();
const audioPlayer = ref<HTMLAudioElement | null>(null);
const isSeeking = ref(false);
const userHasInteracted = ref(false);
const showQueuePopup = ref(false);

const titleContainerRef = ref<HTMLElement | null>(null);
const titleTextContentRef = ref<HTMLElement | null>(null);
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

const hasActiveTrack = computed(() => !!playerStore.currentTrack);

function formatTime(secs: number): string {
  if (isNaN(secs) || !isFinite(secs) || secs < 0) return "0:00";
  const minutes = Math.floor(secs / 60);
  const seconds = Math.floor(secs % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

const checkTextOverflow = () => {
  isTitleOverflowing.value = false;
  isArtistOverflowing.value = false;
  if (!hasActiveTrack.value) return; // Don't check if no track

  nextTick(() => {
    if (titleContainerRef.value && titleTextContentRef.value) {
      const containerWidth = titleContainerRef.value.clientWidth;
      const textWidth = titleTextContentRef.value.scrollWidth;
      if (textWidth > containerWidth) {
        isTitleOverflowing.value = true;
        const scrollDistance = textWidth - containerWidth;
        const scrollSpeed = 40;
        const scrollPhaseDuration = Math.max(2, scrollDistance / scrollSpeed);
        const pausePhaseDuration = 2;
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

const syncAudioElementState = () => {
  if (audioPlayer.value) {
    if (audioPlayer.value.volume !== playerStore.volume) {
      audioPlayer.value.volume = playerStore.volume;
    }
    if (audioPlayer.value.muted !== playerStore.isMuted) {
      audioPlayer.value.muted = playerStore.isMuted;
    }
  }
};

const tryToPlayAudio = () => {
  if (!audioPlayer.value || !audioPlayer.value.src || !hasActiveTrack.value) {
    // Added !hasActiveTrack check
    if (playerStore.isPlaying) playerStore.pauseTrack(); // Ensure store reflects inability to play
    return;
  }
  syncAudioElementState();

  if (playerStore.isPlaying && audioPlayer.value.paused) {
    if (audioPlayer.value.readyState >= 3) {
      audioPlayer.value.play().catch((e) => {
        console.warn(
          "Play failed, possibly due to user interaction policy:",
          e
        );
        if (e.name === "NotAllowedError") {
          playerStore.pauseTrack();
        }
      });
    }
  } else if (!playerStore.isPlaying && !audioPlayer.value.paused) {
    audioPlayer.value.pause();
  }
};

const onLoadedMetadata = () => {
  if (audioPlayer.value && hasActiveTrack.value) {
    // Check hasActiveTrack
    const currentAudioDuration = audioPlayer.value.duration;
    playerStore.setDuration(currentAudioDuration);
    syncAudioElementState();

    const persistedTimeFromStore = playerStore.currentTime;

    if (
      playerStore.currentTrackUrl === audioPlayer.value.src &&
      !isSeeking.value
    ) {
      if (
        persistedTimeFromStore >= 0 &&
        persistedTimeFromStore < currentAudioDuration
      ) {
        if (
          Math.abs(audioPlayer.value.currentTime - persistedTimeFromStore) >
            0.5 ||
          (audioPlayer.value.currentTime === 0 && persistedTimeFromStore > 0)
        ) {
          audioPlayer.value.currentTime = persistedTimeFromStore;
        }
      } else if (
        persistedTimeFromStore >= currentAudioDuration &&
        currentAudioDuration > 0
      ) {
        audioPlayer.value.currentTime =
          currentAudioDuration > 0.1 ? currentAudioDuration - 0.1 : 0;
        playerStore.setCurrentTime(audioPlayer.value.currentTime);
      }
    }
    checkTextOverflow();
  } else if (audioPlayer.value && !hasActiveTrack.value) {
    // No active track, ensure duration is 0
    playerStore.setDuration(0);
  }
};

const onCanPlay = () => {
  if (audioPlayer.value && hasActiveTrack.value) {
    // Check hasActiveTrack
    syncAudioElementState();
    tryToPlayAudio();
  }
};

const onTimeUpdate = () => {
  if (audioPlayer.value && !isSeeking.value && hasActiveTrack.value)
    // Check hasActiveTrack
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
const onEnded = () => {
  if (hasActiveTrack.value) playerStore.handleTrackEnd(); // Check hasActiveTrack
};

watch(
  () => playerStore.currentTrackUrl,
  (newUrl, oldUrl) => {
    isTitleOverflowing.value = false;
    isArtistOverflowing.value = false;

    if (audioPlayer.value) {
      if (newUrl) {
        // If there's a new URL (meaning a track is selected)
        if (newUrl !== audioPlayer.value.src) {
          audioPlayer.value.src = newUrl;
          syncAudioElementState();
          audioPlayer.value.load();
        } else if (playerStore.isPlaying && audioPlayer.value.paused) {
          tryToPlayAudio();
        }
      } else {
        // No new URL (no track selected)
        audioPlayer.value.pause();
        audioPlayer.value.src = "";
        playerStore.setDuration(0); // Explicitly set duration to 0
        playerStore.setCurrentTime(0); // And current time
      }
    }
    // Check text overflow needs to happen after potential DOM updates due to track info change
    nextTick(checkTextOverflow);
  },
  { flush: "post" }
);

watch(
  () => playerStore.isPlaying,
  (playing) => {
    if (!audioPlayer.value) return;
    // Only attempt to play/pause if there is an active track
    if (hasActiveTrack.value || !playing) {
      // Allow pause even if no track (defensive)
      nextTick(tryToPlayAudio);
    } else if (playing && !hasActiveTrack.value) {
      // If store says play but no track, force store to pause
      playerStore.pauseTrack();
    }
  }
);

watch(
  () => playerStore.currentTime,
  (newStoreTime) => {
    if (
      audioPlayer.value &&
      !isSeeking.value &&
      playerStore.duration > 0 &&
      hasActiveTrack.value
    ) {
      const delta = Math.abs(audioPlayer.value.currentTime - newStoreTime);
      if (delta > 0.8) {
        if (newStoreTime >= 0 && newStoreTime <= playerStore.duration) {
          audioPlayer.value.currentTime = newStoreTime;
        }
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
  hasActiveTrack,
  (newHasActiveTrack) => {
    if (!newHasActiveTrack) {
      // If track becomes inactive, ensure internal player state is clean
      if (audioPlayer.value) {
        audioPlayer.value.pause();
        // audioPlayer.value.src = ""; // This is handled by currentTrackUrl watcher
      }
      playerStore.setDuration(0);
      playerStore.setCurrentTime(0);
    }
    // Ensure text overflow is re-checked when track status changes
    checkTextOverflow();
  },
  { immediate: true }
);

const handleProgressSeek = (event: Event) => {
  if (audioPlayer.value && playerStore.duration > 0 && hasActiveTrack.value) {
    const newTime = parseFloat((event.target as HTMLInputElement).value);
    audioPlayer.value.currentTime = newTime;
    playerStore.setCurrentTime(newTime);
  }
};
const onSeekMouseDown = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  if (hasActiveTrack.value) isSeeking.value = true;
};
const onSeekMouseUp = () => {
  isSeeking.value = false;
  if (audioPlayer.value && hasActiveTrack.value) tryToPlayAudio();
};
const handleTogglePlayPauseClick = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  if (hasActiveTrack.value) playerStore.togglePlayPause();
};
const handleVolumeSeek = (event: Event) => {
  // Volume can be adjusted even if no track is playing
  if (!userHasInteracted.value) userHasInteracted.value = true;
  const newVolume = parseFloat((event.target as HTMLInputElement).value);
  playerStore.setVolume(newVolume);
  if (newVolume > 0 && playerStore.isMuted) playerStore.setMuted(false);
};
const toggleQueuePopup = () => (showQueuePopup.value = !showQueuePopup.value);

let resizeObserver: ResizeObserver | null = null;
onMounted(() => {
  if (audioPlayer.value) {
    syncAudioElementState();
    if (playerStore.currentTrackUrl) {
      // implies hasActiveTrack is true or will soon be
      if (audioPlayer.value.src !== playerStore.currentTrackUrl) {
        audioPlayer.value.src = playerStore.currentTrackUrl;
      } else {
        if (audioPlayer.value.readyState >= 1) {
          onLoadedMetadata();
        }
      }
    } else {
      // No track URL on mount
      playerStore.setDuration(0);
      playerStore.setCurrentTime(0);
    }
  }

  if (titleContainerRef.value && artistContainerRef.value) {
    resizeObserver = new ResizeObserver(checkTextOverflow);
    if (titleContainerRef.value)
      resizeObserver.observe(titleContainerRef.value);
    if (artistContainerRef.value)
      resizeObserver.observe(artistContainerRef.value);
  }
  checkTextOverflow();
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
  <div class="audio-player-bar">
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
          v-if="playerStore.currentTrackCoverArtUrl && hasActiveTrack"
          :src="playerStore.currentTrackCoverArtUrl"
          alt="Cover Art"
          class="cover-art-small"
        />
        <div v-else class="cover-art-small placeholder"></div>

        <div class="track-details">
          <template v-if="hasActiveTrack">
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
          </template>
          <template v-else>
            <div class="title-container no-track-info">
              <span>No track selected</span>
            </div>
          </template>
        </div>
      </div>

      <div class="player-controls-main">
        <button
          @click="playerStore.playPreviousInQueue()"
          title="Previous"
          :disabled="!hasActiveTrack"
        >
          ⏮
        </button>
        <button
          @click="handleTogglePlayPauseClick"
          class="play-pause-btn"
          :title="playerStore.isPlaying ? 'Pause' : 'Play'"
          :disabled="!hasActiveTrack"
        >
          {{ playerStore.isPlaying && hasActiveTrack ? "❚❚" : "►" }}
        </button>
        <button
          @click="playerStore.playNextInQueue()"
          title="Next"
          :disabled="!hasActiveTrack"
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
          :value="hasActiveTrack ? playerStore.currentTime : 0"
          :max="hasActiveTrack ? playerStore.duration || 0 : 0"
          step="0.1"
          @input="handleProgressSeek"
          @change="handleProgressSeek"
          @mousedown="onSeekMouseDown"
          @mouseup="onSeekMouseUp"
          :disabled="!hasActiveTrack || !playerStore.duration"
        />
        <span class="time-display total-time">{{
          hasActiveTrack ? formattedDuration : "0:00"
        }}</span>
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
          :value="playerStore.isMuted ? 0 : playerStore.volume"
          @input="handleVolumeSeek"
        />
        <button
          @click="playerStore.cycleRepeatMode()"
          :title="`Repeat: ${playerStore.repeatMode}`"
          class="repeat-button"
          :disabled="!hasActiveTrack"
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

/* No longer need .audio-player-bar-placeholder as bar is always shown */

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
  display: flex; /* Ensure placeholder icon/text can be centered */
  align-items: center;
  justify-content: center;
  font-size: 0.8em; /* Example for text inside placeholder */
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
  height: 1.3em; /* Ensure consistent height */
}

.title-container.no-track-info span {
  font-style: italic;
  color: var(
    --c-player-artist
  ); /* Use a slightly dimmer color for placeholder */
}
.artist-container.no-track-info {
  height: 1.1em; /* Consistent height for artist line */
}

.text-animate-wrapper {
  display: inline-block;
  white-space: nowrap;
}

.text-animate-wrapper.marquee-spotify-refined {
  animation-name: spotify-scroll-refined;
  animation-timing-function: linear;
  animation-iteration-count: infinite;
  animation-duration: var(--animation-duration, 10s);
  will-change: transform;
}

.text-animate-wrapper.marquee-spotify-refined:hover {
  animation-play-state: paused;
}

.text-content {
  display: inline-block;
}

.title-container .text-content {
  font-weight: 500;
  color: var(--c-player-title, #000);
}
.artist-container .text-content {
  font-size: 0.85em;
  color: var(--c-player-artist, #555);
}

@keyframes spotify-scroll-refined {
  0% {
    transform: translateX(0);
  }
  20% {
    transform: translateX(0);
  }
  70% {
    transform: translateX(var(--text-scroll-amount-to-end));
  }
  90% {
    transform: translateX(var(--text-scroll-amount-to-end));
  }
  100% {
    transform: translateX(0);
  }
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
.progress-bar:disabled {
  cursor: not-allowed;
  background: var(
    --c-progress-thumb-disabled-border,
    #ccc
  ); /* More subtle disabled track */
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
.progress-bar:disabled::-webkit-slider-thumb {
  background: var(--c-progress-thumb-disabled-bg, #999);
  border-color: var(--c-progress-thumb-disabled-border, #ccc);
  cursor: not-allowed;
  width: 12px; /* Smaller thumb when disabled */
  height: 12px;
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
.progress-bar:disabled::-moz-range-thumb {
  background: var(--c-progress-thumb-disabled-bg, #999);
  border-color: var(--c-progress-thumb-disabled-border, #ccc);
  cursor: not-allowed;
  width: 12px;
  height: 12px;
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
.player-controls-side button:hover:not(:disabled) {
  color: var(--c-player-controls-side-icon-hover, #007bff);
}
.player-controls-side button:disabled {
  color: var(--c-player-controls-disabled, #aaa);
  cursor: not-allowed;
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
