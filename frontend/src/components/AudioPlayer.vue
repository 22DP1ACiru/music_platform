<script setup lang="ts">
import { ref, watch, onMounted, computed, nextTick } from "vue";
import { usePlayerStore } from "@/stores/player";

const playerStore = usePlayerStore();
const audioPlayer = ref<HTMLAudioElement | null>(null);
const isSeeking = ref(false);
const userHasInteracted = ref(false); // To track if user has interacted for autoplay policies

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

const tryToPlayAudio = () => {
  if (!audioPlayer.value || !audioPlayer.value.src) {
    console.log(
      "AudioPlayer: tryToPlayAudio - Aborted: No audio element or src."
    );
    return;
  }

  if (playerStore.isPlaying && audioPlayer.value.paused) {
    // readyState 3 (HAVE_FUTURE_DATA) or 4 (HAVE_ENOUGH_DATA) is generally good.
    // Some recommend waiting for HAVE_ENOUGH_DATA (4) for robust play.
    if (audioPlayer.value.readyState >= 3) {
      console.log(
        `AudioPlayer: tryToPlayAudio - Player ready (state ${audioPlayer.value.readyState}). Attempting play().`
      );
      const playPromise = audioPlayer.value.play();
      if (playPromise !== undefined) {
        playPromise.catch((error) => {
          console.warn("AudioPlayer: tryToPlayAudio - Playback failed:", error);
          // If play is rejected, we might need to update store state to paused
          // if (playerStore.isPlaying) playerStore.pauseTrack();
        });
      }
    } else {
      console.log(
        `AudioPlayer: tryToPlayAudio - Player not ready enough (state ${audioPlayer.value.readyState}). Play will be attempted on 'canplay'.`
      );
      // If not ready, 'canplay' event should eventually trigger this function again.
      // If src just changed, audioPlayer.value.load() was called, which leads to 'canplay'.
    }
  } else if (!playerStore.isPlaying && !audioPlayer.value.paused) {
    console.log(
      "AudioPlayer: tryToPlayAudio - Store wants pause, player is playing. Pausing."
    );
    audioPlayer.value.pause();
  } else {
    // console.log(`AudioPlayer: tryToPlayAudio - Conditions not met. isPlaying: ${playerStore.isPlaying}, paused: ${audioPlayer.value.paused}, readyState: ${audioPlayer.value.readyState}`);
  }
};

const onLoadedMetadata = () => {
  if (audioPlayer.value) {
    console.log(
      "AudioPlayer: LoadedMetadata event. Duration:",
      audioPlayer.value.duration,
      "ReadyState:",
      audioPlayer.value.readyState
    );
    playerStore.setDuration(audioPlayer.value.duration);
  }
};

const onCanPlay = () => {
  if (audioPlayer.value) {
    console.log(
      "AudioPlayer: CanPlay event. ReadyState:",
      audioPlayer.value.readyState
    );
    // This is a key moment to try playing if the store expects it.
    tryToPlayAudio();
  }
};

const onTimeUpdate = () => {
  if (audioPlayer.value && !isSeeking.value) {
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
  console.log("AudioPlayer: Ended event");
  playerStore.handleTrackEnd();
};

// Watchers
watch(
  () => playerStore.currentTrackUrl,
  (newUrl, oldUrl) => {
    if (audioPlayer.value && newUrl) {
      console.log(
        `AudioPlayer: currentTrackUrl watcher. New: ${newUrl}, Old: ${oldUrl}, Player src: ${audioPlayer.value.src}`
      );
      // If the new URL is genuinely different from the player's current source
      if (newUrl !== audioPlayer.value.src) {
        audioPlayer.value.src = newUrl;
        playerStore.resetTimes();
        console.log(
          "AudioPlayer: currentTrackUrl watcher - Calling load() for new track URL."
        );
        audioPlayer.value.load(); // This will trigger 'canplay' where tryToPlayAudio is called
      }
      // This handles "repeat one" or if store state changes to play for the *same* track
      // and it's currently paused.
      else if (
        playerStore.isPlaying &&
        audioPlayer.value.paused &&
        newUrl === oldUrl
      ) {
        console.log(
          "AudioPlayer: currentTrackUrl watcher - URL same, but store wants play (e.g., repeat one)."
        );
        tryToPlayAudio();
      }
    } else if (audioPlayer.value && !newUrl) {
      console.log("AudioPlayer: currentTrackUrl watcher - URL cleared.");
      audioPlayer.value.pause();
      audioPlayer.value.src = "";
      playerStore.resetTimes();
    }
  },
  { flush: "post" } // flush: 'post' to ensure DOM updates (like audio src) are processed before watcher logic if needed.
);

watch(
  () => playerStore.isPlaying,
  (shouldPlay, wasPlaying) => {
    if (!audioPlayer.value) return;
    console.log(
      `AudioPlayer: isPlaying watcher. Store wants play: ${shouldPlay}. Player currently paused: ${audioPlayer.value.paused}. WasPlaying: ${wasPlaying}`
    );

    // Call tryToPlayAudio which centralizes play/pause logic based on readiness and store state.
    // Using nextTick to ensure other state changes (like src) have a chance to settle.
    nextTick(() => {
      tryToPlayAudio();
    });
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

const handleProgressSeek = (event: Event) => {
  if (audioPlayer.value && playerStore.duration > 0) {
    const target = event.target as HTMLInputElement;
    const newTime = parseFloat(target.value);
    audioPlayer.value.currentTime = newTime;
    // For immediate visual feedback of the time display during drag:
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
  if (playerStore.isPlaying && audioPlayer.value?.paused) {
    tryToPlayAudio();
  }
};

const handleTogglePlayPauseClick = () => {
  if (!userHasInteracted.value) userHasInteracted.value = true;
  playerStore.togglePlayPause();
  // The isPlaying watcher will call tryToPlayAudio
};

const handleVolumeSeek = (event: Event) => {
  if (audioPlayer.value) {
    if (!userHasInteracted.value) userHasInteracted.value = true;
    const target = event.target as HTMLInputElement;
    const newVolume = parseFloat(target.value);
    playerStore.setVolume(newVolume);
    if (newVolume > 0 && playerStore.isMuted) {
      playerStore.setMuted(false);
    }
  }
};

onMounted(() => {
  if (audioPlayer.value) {
    audioPlayer.value.volume = playerStore.volume;
    audioPlayer.value.muted = playerStore.isMuted;

    if (playerStore.currentTrackUrl) {
      console.log(
        "AudioPlayer: onMounted - Store has currentTrackUrl:",
        playerStore.currentTrackUrl,
        "Player src is:",
        audioPlayer.value.src
      );
      // If the player's src isn't already what the store thinks it should be, set it.
      // The `currentTrackUrl` watcher will handle calling `load()`.
      if (audioPlayer.value.src !== playerStore.currentTrackUrl) {
        audioPlayer.value.src = playerStore.currentTrackUrl;
        // Explicitly load if src was empty, otherwise watcher will handle it.
        // This is mainly for the case where component mounts and store already has a track.
        if (!audioPlayer.value.src || oldSrc === "") {
          // oldSrc would be empty string initially
          console.log(
            "AudioPlayer: onMounted - Player src was empty or different, explicitly loading."
          );
          audioPlayer.value.load();
        }
      }
      // tryToPlayAudio() will be called from `onCanPlay` or `isPlaying` watcher.
    }
    console.log(
      "AudioPlayer.vue mounted. Initial volume:",
      audioPlayer.value.volume,
      "Muted:",
      audioPlayer.value.muted
    );
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
</script>

<template>
  <div class="audio-player-bar" v-if="playerStore.currentTrack">
    <audio
      ref="audioPlayer"
      @loadedmetadata="onLoadedMetadata"
      @canplay="onCanPlay"
      @timeupdate="onTimeUpdate"
      @volumechange="onVolumeChange"
      @ended="onEnded"
      @error="(e) => console.error('Audio Element Error:', (e.target as HTMLAudioElement).error?.code, (e.target as HTMLAudioElement).error?.message)"
      preload="auto"
    >
      Your browser does not support the audio element.
    </audio>

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
          <span class="title">{{
            playerStore.currentTrackDisplayInfo.title
          }}</span>
          <span class="artist">{{
            playerStore.currentTrackDisplayInfo.artist
          }}</span>
        </div>
      </div>

      <div class="player-controls-main">
        <button @click="playerStore.playPreviousInQueue()" title="Previous">
          ⏮
        </button>
        <button
          @click="handleTogglePlayPauseClick"
          class="play-pause-btn"
          :title="playerStore.isPlaying ? 'Pause' : 'Play'"
        >
          {{ playerStore.isPlaying ? "❚❚" : "►" }}
        </button>
        <button @click="playerStore.playNextInQueue()" title="Next">⏭</button>
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
          :disabled="!playerStore.duration"
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
  min-width: 180px;
  max-width: 30%;
  flex-shrink: 1;
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
  white-space: nowrap;
}
.track-details .title,
.track-details .artist {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.track-details .title {
  font-weight: 500;
  color: var(--c-player-title, #000);
}
.track-details .artist {
  font-size: 0.85em;
  color: var(--c-player-artist, #555);
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
.player-controls-main button:hover {
  color: var(--c-player-controls-main-icon-hover, #007bff);
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
.play-pause-btn:hover {
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
}
.progress-bar:disabled::-moz-range-thumb {
  background: var(--c-progress-thumb-disabled-bg, #999);
  border-color: var(--c-progress-thumb-disabled-border, #ccc);
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
}
.player-controls-side button:hover {
  color: var(--c-player-controls-side-icon-hover, #007bff);
}
.repeat-button {
  min-width: 2em;
  text-align: center;
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
}
.volume-slider:disabled::-moz-range-thumb {
  background: var(--c-volume-thumb-disabled-bg, #999);
}

/*
CSS Custom Properties for Theming (define these in your global styles, e.g., base.css or main.css)
(Make sure these are defined in your actual global CSS for the player to look correct)
:root { 
  --c-player-bg: #f8f9fa; 
  --c-player-border: #dee2e6;
  ... (rest of the variables) ...
}
@media (prefers-color-scheme: dark) {
  :root { 
    --c-player-bg: #212529;
    --c-player-border: #343a40;
    ... (rest of the variables) ...
  }
}
*/
</style>
