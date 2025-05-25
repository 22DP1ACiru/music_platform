import { defineStore } from "pinia";
import { ref, computed } from "vue";

// Interface for track info needed by the player
export interface PlayerTrackInfo {
  id: number; // Unique ID for the track
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
  const queue = ref<PlayerTrackInfo[]>([]);
  const currentQueueIndex = ref(-1); // Index of the currentTrack within the queue

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

  // --- Internal Helper to Start Playback ---
  function _startPlayback(track: PlayerTrackInfo) {
    currentTrack.value = track;
    duration.value = track.duration || 0;
    currentTime.value = 0;
    isPlaying.value = true;
    console.log(
      "Player Store: Starting playback for",
      track.title,
      "at index",
      currentQueueIndex.value
    );
  }

  // --- Actions ---

  function setQueueAndPlay(tracks: PlayerTrackInfo[], startIndex: number = 0) {
    console.log(
      "Player Store: Setting new queue and playing. Tracks count:",
      tracks.length,
      "Start index:",
      startIndex
    );
    if (!tracks || tracks.length === 0) {
      console.warn(
        "Player Store: setQueueAndPlay called with empty tracks array."
      );
      queue.value = [];
      currentTrack.value = null;
      isPlaying.value = false;
      currentQueueIndex.value = -1;
      resetTimes();
      return;
    }
    if (startIndex < 0 || startIndex >= tracks.length) {
      console.warn(
        "Player Store: setQueueAndPlay called with invalid startIndex. Defaulting to 0."
      );
      startIndex = 0;
    }

    queue.value = [...tracks];
    currentQueueIndex.value = startIndex;
    _startPlayback(queue.value[startIndex]);
  }

  function playTrack(track: PlayerTrackInfo) {
    console.log("Player Store: Play single track requested", track.title);
    setQueueAndPlay([track], 0);
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
    if (
      !currentTrack.value &&
      queue.value.length > 0 &&
      currentQueueIndex.value !== -1 &&
      currentQueueIndex.value < queue.value.length
    ) {
      _startPlayback(queue.value[currentQueueIndex.value]);
    } else if (!currentTrack.value && queue.value.length > 0) {
      setQueueAndPlay(queue.value, 0);
    } else if (currentTrack.value) {
      isPlaying.value = !isPlaying.value;
    }
  }

  function playNextInQueue() {
    console.log(
      "Player Store: playNextInQueue called. Current index:",
      currentQueueIndex.value,
      "Queue length:",
      queue.value.length,
      "Repeat mode:",
      repeatMode.value
    );
    if (queue.value.length === 0) {
      console.log("Player Store: Queue empty, cannot play next.");
      currentTrack.value = null;
      isPlaying.value = false;
      currentQueueIndex.value = -1;
      resetTimes();
      return;
    }

    let nextIndex = currentQueueIndex.value + 1;

    if (nextIndex >= queue.value.length) {
      if (repeatMode.value === "all") {
        console.log("Player Store: End of queue, repeating all.");
        nextIndex = 0;
      } else {
        console.log(
          "Player Store: End of queue, repeat mode is not 'all'. Stopping."
        );
        isPlaying.value = false;
        // Optional: Reset currentTime to 0 or keep it at duration for the last track
        currentTime.value = duration.value; // Show as finished
        // currentQueueIndex.value = -1; // Or keep it at last index
        // currentTrack.value = null; // Or keep last track visible
        return;
      }
    }

    currentQueueIndex.value = nextIndex;
    _startPlayback(queue.value[nextIndex]);
  }

  function playPreviousInQueue() {
    console.log(
      "Player Store: playPreviousInQueue called. Current index:",
      currentQueueIndex.value
    );
    if (queue.value.length === 0) {
      console.log("Player Store: Queue empty, cannot play previous.");
      return;
    }

    if (currentTime.value > 3 && currentTrack.value) {
      console.log("Player Store: Replaying current track from beginning.");
      currentTime.value = 0;
      isPlaying.value = true;
      return;
    }

    let prevIndex = currentQueueIndex.value - 1;

    if (prevIndex < 0) {
      if (repeatMode.value === "all") {
        console.log(
          "Player Store: Start of queue, repeating all (to last track)."
        );
        prevIndex = queue.value.length - 1;
      } else {
        console.log(
          "Player Store: Start of queue, repeat mode is not 'all'. Replaying current or doing nothing."
        );
        if (currentTrack.value) {
          currentTime.value = 0;
          isPlaying.value = true;
        }
        return;
      }
    }
    currentQueueIndex.value = prevIndex;
    _startPlayback(queue.value[prevIndex]);
  }

  function handleTrackEnd() {
    console.log("Player Store: Track ended. Repeat mode:", repeatMode.value);
    if (repeatMode.value === "one" && currentTrack.value) {
      console.log("Player Store: Repeating one track.");
      currentTime.value = 0;
      isPlaying.value = true;
    } else {
      console.log(
        "Player Store: Track ended, calling playNextInQueue for mode:",
        repeatMode.value
      );
      playNextInQueue();
    }
  }

  function setCurrentTime(time: number) {
    currentTime.value = time;
  }

  function setDuration(time: number) {
    duration.value = time;
  }

  function setVolume(vol: number) {
    volume.value = Math.max(0, Math.min(1, vol));
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
    if (repeatMode.value === "none") setRepeatMode("all");
    else if (repeatMode.value === "all") setRepeatMode("one");
    else setRepeatMode("none");
    console.log("Player Store: Cycled repeat mode to:", repeatMode.value);
  }

  function resetTimes() {
    currentTime.value = 0;
    duration.value = 0;
  }

  function clearQueue() {
    console.log("Player Store: Clearing queue.");
    queue.value = [];
    currentTrack.value = null; // Clear current track when queue is cleared
    isPlaying.value = false;
    currentQueueIndex.value = -1;
    resetTimes();
  }

  function addTrackToQueue(track: PlayerTrackInfo) {
    console.log("Player Store: Adding track to queue", track.title);
    const existingTrackIndex = queue.value.findIndex((t) => t.id === track.id);
    if (existingTrackIndex === -1) {
      // Add only if not already in queue
      queue.value.push(track);
    }
    if (!currentTrack.value && queue.value.length > 0) {
      // If nothing is playing, and queue was empty or just got first item
      currentQueueIndex.value = queue.value.findIndex((t) => t.id === track.id); // find it in case it was already there
      if (currentQueueIndex.value === -1 && queue.value.length === 1)
        currentQueueIndex.value = 0; // if truly new and only one

      if (currentQueueIndex.value !== -1 && !isPlaying.value) {
        _startPlayback(queue.value[currentQueueIndex.value]);
      } else if (queue.value.length === 1) {
        // If it's the very first track in an empty player
        _startPlayback(queue.value[0]);
      }
    }
  }

  function playTrackFromQueueByIndex(index: number) {
    if (index >= 0 && index < queue.value.length) {
      currentQueueIndex.value = index;
      _startPlayback(queue.value[index]);
    } else {
      console.warn(
        "Player Store: Invalid index for playTrackFromQueueByIndex",
        index
      );
    }
  }

  function removeTrackFromQueue(indexToRemove: number) {
    if (indexToRemove < 0 || indexToRemove >= queue.value.length) {
      console.warn(
        "Player Store: Invalid index for removeFromQueue",
        indexToRemove
      );
      return;
    }

    const isRemovingCurrentTrack = currentQueueIndex.value === indexToRemove;
    const wasPlaying = isPlaying.value;

    queue.value.splice(indexToRemove, 1);
    console.log(
      "Player Store: Removed track at index",
      indexToRemove,
      "New queue length:",
      queue.value.length
    );

    if (queue.value.length === 0) {
      currentTrack.value = null;
      isPlaying.value = false;
      currentQueueIndex.value = -1;
      resetTimes();
      console.log("Player Store: Queue empty after removal. Playback stopped.");
      return;
    }

    if (isRemovingCurrentTrack) {
      // If the current track was removed, play the next available track, or the new first track if it was the last.
      // Or stop if that was the only track.
      let newIndexToPlay = indexToRemove;
      if (newIndexToPlay >= queue.value.length) {
        // If last track was removed
        newIndexToPlay = 0; // Go to first track, or could be queue.value.length -1 for previous
      }
      currentQueueIndex.value = newIndexToPlay; // Update current index regardless
      if (wasPlaying) {
        // Only auto-play if it was playing before
        _startPlayback(queue.value[newIndexToPlay]);
      } else {
        // If it was paused, update currentTrack but don't auto-play
        currentTrack.value = queue.value[newIndexToPlay];
        // duration.value and currentTime.value should ideally be reset or reflect the new track
        duration.value = currentTrack.value.duration || 0;
        currentTime.value = 0;
      }
      console.log(
        "Player Store: Removed current track. New current track at index",
        newIndexToPlay
      );
    } else if (indexToRemove < currentQueueIndex.value) {
      // If a track before the current one was removed, adjust current index
      currentQueueIndex.value--;
      console.log(
        "Player Store: Removed track before current. Adjusted currentQueueIndex to",
        currentQueueIndex.value
      );
    }
    // If a track after the current one was removed, currentQueueIndex and currentTrack are still valid.
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
    queue,
    currentQueueIndex,

    // Getters
    currentTrackUrl,
    currentTrackCoverArtUrl,
    currentTrackDisplayInfo,

    // Actions
    playTrack,
    setQueueAndPlay,
    addTrackToQueue,
    clearQueue,
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
    playNextInQueue,
    playPreviousInQueue,
    resetTimes,
    playTrackFromQueueByIndex, // New
    removeTrackFromQueue, // New
  };
});
