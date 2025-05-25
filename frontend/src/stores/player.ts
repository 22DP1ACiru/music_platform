import { defineStore } from "pinia";
import { ref, computed } from "vue";

// Interface for track info needed by the player
export interface PlayerTrackInfo {
  id: number;
  title: string;
  audio_file: string; // The URL to play
  artistName?: string;
  releaseTitle?: string;
  coverArtUrl?: string | null;
  duration?: number | null; // Duration in seconds
}

export const usePlayerStore = defineStore("player", () => {
  // --- State ---
  const currentTrack = ref<PlayerTrackInfo | null>(null);
  const isPlaying = ref(false);
  const currentTime = ref(0);
  const duration = ref(0);

  const initialVolume = parseFloat(
    localStorage.getItem("playerVolume") || "0.75"
  );
  const volume = ref(initialVolume);

  const initialMuted = JSON.parse(
    localStorage.getItem("playerMuted") || "false"
  );
  const isMuted = ref(initialMuted);

  const initialRepeatMode = (localStorage.getItem("playerRepeatMode") ||
    "none") as "none" | "one" | "all";
  const repeatMode = ref<"none" | "one" | "all">(initialRepeatMode);

  // --- Getters ---
  const currentTrackUrl = computed(
    () => currentTrack.value?.audio_file || null
  );
  const currentTrackCoverArtUrl = computed(
    () => currentTrack.value?.coverArtUrl || null
  );
  const currentTrackDisplayInfo = computed(() => {
    if (!currentTrack.value)
      return { title: "No track selected", artist: "", coverArtUrl: null };
    return {
      title: currentTrack.value.title,
      artist: currentTrack.value.artistName || "Unknown Artist",
      coverArtUrl: currentTrack.value.coverArtUrl,
    };
  });

  // --- Actions ---
  function playTrack(track: PlayerTrackInfo) {
    console.log("Player Store: Play track requested", track);
    currentTrack.value = track;
    duration.value = track.duration || 0; // Set duration from track info
    currentTime.value = 0; // Reset current time for new track
    isPlaying.value = true;
  }

  function pauseTrack() {
    console.log("Player Store: Pause requested");
    isPlaying.value = false;
  }

  function resumeTrack() {
    console.log("Player Store: Resume requested");
    if (currentTrack.value) {
      isPlaying.value = true;
    }
  }

  function togglePlayPause() {
    if (!currentTrack.value && queue.value.length > 0) {
      // Basic queue interaction placeholder
      playTrack(queue.value[0]); // Play first in queue if nothing current
    } else if (currentTrack.value) {
      isPlaying.value = !isPlaying.value;
    }
  }

  function setCurrentTime(time: number) {
    currentTime.value = time;
  }

  function setDuration(time: number) {
    duration.value = time;
  }

  function setVolume(vol: number) {
    volume.value = Math.max(0, Math.min(1, vol)); // Clamp between 0 and 1
    localStorage.setItem("playerVolume", volume.value.toString());
  }

  function setMuted(muted: boolean) {
    isMuted.value = muted;
    localStorage.setItem("playerMuted", JSON.stringify(muted));
  }

  function toggleMute() {
    setMuted(!isMuted.value);
  }

  function setRepeatMode(mode: "none" | "one" | "all") {
    repeatMode.value = mode;
    localStorage.setItem("playerRepeatMode", mode);
  }

  function cycleRepeatMode() {
    if (repeatMode.value === "none") setRepeatMode("one");
    else if (repeatMode.value === "one") setRepeatMode("all");
    else setRepeatMode("none");
  }

  function handleTrackEnd() {
    console.log("Player Store: Track ended. Repeat mode:", repeatMode.value);
    if (repeatMode.value === "one" && currentTrack.value) {
      currentTime.value = 0;
      isPlaying.value = true; // Signal to replay
    } else if (repeatMode.value === "all") {
      // TODO: Implement play next in queue, loop to start if at end
      // For now, behaves like 'none' if no queue logic
      playNextInQueue();
    } else {
      // 'none' or 'all' with no queue
      isPlaying.value = false;
      currentTime.value = 0; // Optional: reset time, or let it stay at duration
      // Consider if currentTrack should be cleared or if next track should be auto-played
    }
  }

  function resetTimes() {
    currentTime.value = 0;
    duration.value = 0;
  }

  // --- Placeholder for Queue (to be expanded later) ---
  const queue = ref<PlayerTrackInfo[]>([]);
  const currentQueueIndex = ref(-1);

  function addToQueue(track: PlayerTrackInfo) {
    queue.value.push(track);
    // If nothing is playing and queue was empty, start playing this track
    if (!currentTrack.value && queue.value.length === 1) {
      playTrackFromQueue(0);
    }
  }

  function playTrackFromQueue(index: number) {
    if (index >= 0 && index < queue.value.length) {
      currentQueueIndex.value = index;
      playTrack(queue.value[index]);
    }
  }

  function playNextInQueue() {
    if (queue.value.length === 0) {
      isPlaying.value = false; // Nothing to play
      return;
    }
    let nextIndex = currentQueueIndex.value + 1;
    if (nextIndex >= queue.value.length) {
      if (repeatMode.value === "all") {
        // Loop queue
        nextIndex = 0;
      } else {
        // End of queue, no loop all
        isPlaying.value = false;
        currentTime.value = 0;
        // Optionally clear currentTrack or just stop
        // currentTrack.value = null;
        return;
      }
    }
    playTrackFromQueue(nextIndex);
  }

  function playPreviousInQueue() {
    if (queue.value.length === 0) return;
    let prevIndex = currentQueueIndex.value - 1;
    if (prevIndex < 0) {
      if (repeatMode.value === "all") {
        // Loop queue to end
        prevIndex = queue.value.length - 1;
      } else {
        // Start of queue, no loop all
        // Optionally replay current if desired or just do nothing
        if (currentTrack.value) {
          // Replay current if at beginning
          currentTime.value = 0;
          isPlaying.value = true;
        }
        return;
      }
    }
    if (prevIndex < 0 && queue.value.length > 0) prevIndex = 0; // safety for empty or single item queue
    playTrackFromQueue(prevIndex);
  }

  return {
    // State
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    repeatMode,
    queue, // Expose queue for potential future UI
    currentQueueIndex, // Expose for potential future UI

    // Getters
    currentTrackUrl,
    currentTrackCoverArtUrl,
    currentTrackDisplayInfo,

    // Actions
    playTrack,
    pauseTrack,
    resumeTrack,
    togglePlayPause,
    setCurrentTime,
    setDuration,
    setVolume,
    setMuted,
    toggleMute,
    setRepeatMode,
    cycleRepeatMode,
    handleTrackEnd,
    resetTimes,
    addToQueue,
    playNextInQueue,
    playPreviousInQueue,
  };
});
