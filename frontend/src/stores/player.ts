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

  /**
   * Sets a new queue and starts playing from a specific track in that queue.
   * This is typically used when a user decides to play a collection (e.g., an album or playlist).
   */
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
      clearQueue();
      currentTrack.value = null;
      isPlaying.value = false;
      return;
    }
    if (startIndex < 0 || startIndex >= tracks.length) {
      console.warn(
        "Player Store: setQueueAndPlay called with invalid startIndex. Defaulting to 0."
      );
      startIndex = 0;
    }

    queue.value = [...tracks]; // Create a new array to ensure reactivity
    currentQueueIndex.value = startIndex;
    _startPlayback(queue.value[startIndex]);
  }

  /**
   * Plays a single track. This action will typically clear the current queue
   * and set the new queue to contain only this track.
   * If you want to play a track as part of a larger queue (e.g., an album),
   * use `setQueueAndPlay` instead.
   */
  function playTrack(track: PlayerTrackInfo) {
    console.log("Player Store: Play single track requested", track.title);
    setQueueAndPlay([track], 0); // Clears old queue, sets new queue with just this track
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
      currentQueueIndex.value !== -1
    ) {
      // If no current track but there's a queue and a valid index (e.g., after stopping at end)
      _startPlayback(queue.value[currentQueueIndex.value]);
    } else if (!currentTrack.value && queue.value.length > 0) {
      // If no current track, but queue has items, play the first one.
      setQueueAndPlay(queue.value, 0);
    } else if (currentTrack.value) {
      isPlaying.value = !isPlaying.value;
    }
    // If no currentTrack and no queue, nothing happens.
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
      isPlaying.value = false;
      currentTrack.value = null; // Clear track if queue is gone
      return;
    }

    let nextIndex = currentQueueIndex.value + 1;

    if (nextIndex >= queue.value.length) {
      // If at the end of the queue
      if (repeatMode.value === "all") {
        console.log("Player Store: End of queue, repeating all.");
        nextIndex = 0; // Loop to the beginning
      } else {
        console.log(
          "Player Store: End of queue, repeat mode is not 'all'. Stopping."
        );
        isPlaying.value = false;
        currentTime.value = duration.value; // Or 0, show track as finished
        // Don't clear currentTrack or queue here, user might want to replay or see what was last.
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

    // If current time is more than a few seconds, replay current track from start
    if (currentTime.value > 3 && currentTrack.value) {
      console.log("Player Store: Replaying current track from beginning.");
      currentTime.value = 0;
      isPlaying.value = true; // Ensure it plays
      return;
    }

    let prevIndex = currentQueueIndex.value - 1;

    if (prevIndex < 0) {
      // If at the beginning of the queue
      if (repeatMode.value === "all") {
        console.log(
          "Player Store: Start of queue, repeating all (to last track)."
        );
        prevIndex = queue.value.length - 1; // Loop to the end
      } else {
        console.log(
          "Player Store: Start of queue, repeat mode is not 'all'. Replaying current or doing nothing."
        );
        // Replay current track from start if not already handled by currentTime check
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
      isPlaying.value = true; // Signal to replay
    } else {
      // For 'all' and 'none', playNextInQueue handles the logic including stopping for 'none' at end of queue
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
    if (repeatMode.value === "none")
      setRepeatMode("all"); // Changed cycle order: none -> all -> one
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
    currentQueueIndex.value = -1;
    // Optionally stop playback and clear current track if it was part of the cleared queue
    // currentTrack.value = null;
    // isPlaying.value = false;
    // resetTimes();
  }

  // New action to add a single track to the end of the existing queue
  function addTrackToQueue(track: PlayerTrackInfo) {
    console.log("Player Store: Adding track to queue", track.title);
    queue.value.push(track);
    // If nothing is playing and this is the first track added, start playing it.
    if (!currentTrack.value && queue.value.length === 1) {
      currentQueueIndex.value = 0;
      _startPlayback(queue.value[0]);
    }
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
    playTrack, // Plays a single track, replacing the queue
    setQueueAndPlay, // Sets a list of tracks as the queue and plays from an index
    addTrackToQueue, // Adds a single track to the end of the current queue
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
  };
});
