import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import type { PlayerTrackInfo } from "@/types";
import axios from "axios";
import { useAuthStore } from "./auth"; // Import AuthStore

interface PersistedPlayerState {
  persistedTrack: PlayerTrackInfo | null;
  persistedQueue: PlayerTrackInfo[];
  persistedQueueIndex: number;
  persistedCurrentTime: number;
  persistedVolume: number;
  persistedIsMuted: boolean;
  persistedRepeatMode: "none" | "one" | "all";
}

const PLAYER_STORAGE_KEY = "vaultwavePlayerState";
const MIN_LOGGABLE_SEGMENT_MS = 2000;

export const usePlayerStore = defineStore("player", () => {
  const authStore = useAuthStore(); // Initialize AuthStore

  const loadInitialState = (): Partial<PersistedPlayerState> => {
    const storedStateRaw = localStorage.getItem(PLAYER_STORAGE_KEY);
    if (storedStateRaw) {
      try {
        return JSON.parse(storedStateRaw) as PersistedPlayerState;
      } catch (e) {
        console.error("Player Store: Failed to parse persisted state", e);
        localStorage.removeItem(PLAYER_STORAGE_KEY);
      }
    }
    return {
      persistedTrack: null,
      persistedQueue: [],
      persistedQueueIndex: -1,
      persistedCurrentTime: 0,
      persistedVolume: 0.75,
      persistedIsMuted: false,
      persistedRepeatMode: "none",
    };
  };

  const initialState = loadInitialState();

  const currentTrack = ref<PlayerTrackInfo | null>(
    initialState.persistedTrack || null
  );
  const queue = ref<PlayerTrackInfo[]>(initialState.persistedQueue || []);
  const currentQueueIndex = ref<number>(initialState.persistedQueueIndex ?? -1);

  const isPlaying = ref(false);
  const currentTime = ref<number>(
    currentTrack.value && initialState.persistedCurrentTime
      ? initialState.persistedCurrentTime
      : 0
  );
  const duration = ref(0);

  const volumeInternal = ref<number>(initialState.persistedVolume ?? 0.75);
  const isMutedInternal = ref<boolean>(initialState.persistedIsMuted ?? false);
  const repeatMode = ref<"none" | "one" | "all">(
    initialState.persistedRepeatMode ?? "none"
  );

  const unmutedSegmentStartTime = ref<number | null>(null);
  const currentTrackIdForLogging = ref<number | null>(
    initialState.persistedTrack?.id || null
  );

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

  const isMuted = computed(() => isMutedInternal.value);
  const volume = computed(() => volumeInternal.value);

  const isEffectivelyAudible = computed(() => {
    return (
      isPlaying.value && !isMutedInternal.value && volumeInternal.value > 0
    );
  });

  function savePlayerStateToLocalStorage(
    options: { preservePersistedTime?: boolean } = {}
  ) {
    const { preservePersistedTime = false } = options;
    let timeToPersist = currentTime.value;

    if (preservePersistedTime) {
      const storedStateRaw = localStorage.getItem(PLAYER_STORAGE_KEY);
      if (storedStateRaw) {
        try {
          const existingState = JSON.parse(
            storedStateRaw
          ) as PersistedPlayerState;
          timeToPersist = existingState.persistedCurrentTime;
        } catch (e) {
          /* Use currentTime.value as fallback */
        }
      } else {
        timeToPersist = 0;
      }
    }

    if (!currentTrack.value) {
      timeToPersist = 0;
    }

    const stateToPersist: PersistedPlayerState = {
      persistedTrack: currentTrack.value,
      persistedQueue: queue.value,
      persistedQueueIndex: currentQueueIndex.value,
      persistedCurrentTime: timeToPersist,
      persistedVolume: volumeInternal.value,
      persistedIsMuted: isMutedInternal.value,
      persistedRepeatMode: repeatMode.value,
    };

    if (
      stateToPersist.persistedTrack === null &&
      stateToPersist.persistedQueue.length === 0
    ) {
      localStorage.removeItem(PLAYER_STORAGE_KEY);
      return;
    }
    localStorage.setItem(PLAYER_STORAGE_KEY, JSON.stringify(stateToPersist));
  }

  async function logListenSegment(
    trackId: number,
    segmentStartTimeMs: number,
    segmentDurationMs: number
  ) {
    // +++ ADD AUTHENTICATION CHECK +++
    if (!authStore.isLoggedIn) {
      console.log(
        "PlayerStore: User not logged in. Skipping listen segment log."
      );
      return;
    }
    // +++ END AUTHENTICATION CHECK +++

    if (segmentDurationMs < MIN_LOGGABLE_SEGMENT_MS) {
      console.log(
        `PlayerStore: Skipping log for short segment (${segmentDurationMs}ms, min: ${MIN_LOGGABLE_SEGMENT_MS}ms) for track ${trackId}`
      );
      return;
    }

    console.log(
      `PlayerStore: Logging listen segment for track ${trackId}, start: ${new Date(
        segmentStartTimeMs
      ).toISOString()}, duration: ${segmentDurationMs}ms`
    );
    try {
      await axios.post(`/tracks/${trackId}/log_listen_segment/`, {
        segment_start_timestamp_utc: new Date(segmentStartTimeMs).toISOString(),
        segment_duration_ms: Math.round(segmentDurationMs),
      });
    } catch (error) {
      console.error(
        `PlayerStore: Failed to log listen segment for track ${trackId}`,
        error
      );
    }
  }

  function handleUnmutedSegmentEnd(reason: string) {
    if (unmutedSegmentStartTime.value && currentTrackIdForLogging.value) {
      const durationMs = Date.now() - unmutedSegmentStartTime.value;
      console.log(
        `PlayerStore: Unmuted segment ended for track ${currentTrackIdForLogging.value}. Reason: ${reason}. Duration: ${durationMs}ms.`
      );
      logListenSegment(
        // This will now check for auth internally
        currentTrackIdForLogging.value,
        unmutedSegmentStartTime.value,
        durationMs
      );
    }
    unmutedSegmentStartTime.value = null;
  }

  function handleUnmutedSegmentStart() {
    if (unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd(
        "starting new segment (precautionary end in handleUnmutedSegmentStart)"
      );
    }

    if (
      isEffectivelyAudible.value &&
      currentTrack.value &&
      currentTrack.value.id
    ) {
      console.log(
        `PlayerStore: New unmuted segment started for track ${currentTrack.value.id}.`
      );
      unmutedSegmentStartTime.value = Date.now();
      currentTrackIdForLogging.value = currentTrack.value.id;
    } else {
      unmutedSegmentStartTime.value = null;
      currentTrackIdForLogging.value = currentTrack.value?.id || null;
    }
  }

  function handleSeekOperation() {
    console.log("PlayerStore: Seek operation detected.");
    if (unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("seek operation");
    }
    if (isEffectivelyAudible.value) {
      handleUnmutedSegmentStart();
    }
  }

  let currentTimeSaveTimeout: number | undefined;
  watch(currentTime, (newTime) => {
    clearTimeout(currentTimeSaveTimeout);
    if (currentTrack.value) {
      currentTimeSaveTimeout = window.setTimeout(() => {
        savePlayerStateToLocalStorage({ preservePersistedTime: false });
      }, 1000);
    }
  });

  watch(
    currentTrack,
    (newTrack, oldTrack) => {
      currentTrackIdForLogging.value = newTrack?.id || null;
      if (!newTrack && unmutedSegmentStartTime.value) {
        handleUnmutedSegmentEnd("track became null");
      }
      savePlayerStateToLocalStorage({ preservePersistedTime: !newTrack });
    },
    { deep: true }
  );

  watch(isEffectivelyAudible, (newlyAudible, wasAudible) => {
    if (currentTrack.value) {
      if (newlyAudible && !wasAudible) {
        handleUnmutedSegmentStart();
      } else if (!newlyAudible && wasAudible && unmutedSegmentStartTime.value) {
        handleUnmutedSegmentEnd(
          isPlaying.value
            ? isMutedInternal.value
              ? "muted"
              : "volume zero"
            : "paused/stopped"
        );
      }
    } else if (!newlyAudible && unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("no current track and not audible");
    }
  });

  watch(isPlaying, (playing) => {
    savePlayerStateToLocalStorage(
      !playing && currentTrack.value
        ? { preservePersistedTime: false }
        : { preservePersistedTime: true }
    );
  });

  function setMuted(muted: boolean) {
    isMutedInternal.value = muted;
    savePlayerStateToLocalStorage({ preservePersistedTime: true });
  }

  function setVolume(vol: number) {
    const newVolume = Math.max(0, Math.min(1, vol));
    volumeInternal.value = newVolume;
    savePlayerStateToLocalStorage({ preservePersistedTime: true });
  }

  watch(
    [queue, currentQueueIndex],
    () => {
      savePlayerStateToLocalStorage({ preservePersistedTime: true });
    },
    { deep: true }
  );

  watch([repeatMode], () => {
    savePlayerStateToLocalStorage({ preservePersistedTime: true });
  });

  function _startPlayback(track: PlayerTrackInfo) {
    const oldTrackId = currentTrack.value?.id;

    if (
      oldTrackId &&
      oldTrackId !== track.id &&
      unmutedSegmentStartTime.value
    ) {
      handleUnmutedSegmentEnd(`_startPlayback for new track: ${track.title}`);
    } else if (
      oldTrackId &&
      oldTrackId === track.id &&
      unmutedSegmentStartTime.value
    ) {
      handleUnmutedSegmentEnd(
        `_startPlayback replaying same track: ${track.title}`
      );
    }

    currentTrack.value = track;
    currentTrackIdForLogging.value = track.id;

    if (
      currentQueueIndex.value === -1 ||
      queue.value[currentQueueIndex.value]?.id !== track.id
    ) {
      currentTime.value = 0;
    }
    isPlaying.value = true;

    if (isEffectivelyAudible.value) {
      handleUnmutedSegmentStart();
    }
  }

  function setQueueAndPlay(tracks: PlayerTrackInfo[], startIndex: number = 0) {
    if (!tracks || tracks.length === 0) {
      resetPlayerState(false);
      return;
    }
    if (startIndex < 0 || startIndex >= tracks.length) startIndex = 0;

    queue.value = [...tracks];
    currentQueueIndex.value = startIndex;
    _startPlayback(queue.value[startIndex]);
  }

  function playTrack(track: PlayerTrackInfo) {
    setQueueAndPlay([track], 0);
  }

  function pauseTrack() {
    isPlaying.value = false;
  }

  function resumeTrack() {
    if (currentTrack.value) isPlaying.value = true;
  }

  function togglePlayPause() {
    if (!currentTrack.value && queue.value.length > 0) {
      const indexToPlay =
        currentQueueIndex.value !== -1 &&
        currentQueueIndex.value < queue.value.length
          ? currentQueueIndex.value
          : 0;
      if (indexToPlay < queue.value.length) {
        currentQueueIndex.value = indexToPlay;
        _startPlayback(queue.value[indexToPlay]);
      }
    } else if (currentTrack.value) {
      if (
        !isPlaying.value &&
        duration.value > 0 &&
        currentTime.value >= duration.value &&
        repeatMode.value !== "one"
      ) {
        currentTime.value = 0;
      }
      isPlaying.value = !isPlaying.value;
    }
  }

  function playNextInQueue() {
    if (queue.value.length === 0) {
      if (unmutedSegmentStartTime.value)
        handleUnmutedSegmentEnd("queue empty, stopping");
      currentTrack.value = null;
      isPlaying.value = false;
      currentQueueIndex.value = -1;
      resetTimes();
      return;
    }
    let nextIndex = currentQueueIndex.value + 1;
    if (nextIndex >= queue.value.length) {
      if (repeatMode.value === "all") {
        nextIndex = 0;
      } else {
        if (unmutedSegmentStartTime.value)
          handleUnmutedSegmentEnd("queue ended, no repeat all");
        isPlaying.value = false;
        if (duration.value > 0) currentTime.value = duration.value;
        return;
      }
    }
    currentQueueIndex.value = nextIndex;
    _startPlayback(queue.value[nextIndex]);
  }

  function playPreviousInQueue() {
    if (queue.value.length === 0) return;
    if (
      (currentTime.value > 3 && currentTrack.value) ||
      (currentTime.value <= 3 &&
        currentQueueIndex.value === 0 &&
        repeatMode.value !== "all")
    ) {
      if (
        unmutedSegmentStartTime.value &&
        currentTrack.value &&
        currentTime.value > 0
      ) {
        handleUnmutedSegmentEnd("replay current track");
      }
      currentTime.value = 0;
      if (currentTrack.value) {
        isPlaying.value = true;
        if (isEffectivelyAudible.value) handleUnmutedSegmentStart();
      }
      return;
    }
    let prevIndex = currentQueueIndex.value - 1;
    if (prevIndex < 0) {
      if (repeatMode.value === "all") {
        prevIndex = queue.value.length - 1;
      } else {
        if (currentTrack.value) {
          if (
            unmutedSegmentStartTime.value &&
            currentTrack.value &&
            currentTime.value > 0
          ) {
            handleUnmutedSegmentEnd("replay current track at start of queue");
          }
          currentTime.value = 0;
          isPlaying.value = true;
          if (isEffectivelyAudible.value) handleUnmutedSegmentStart();
        }
        return;
      }
    }
    currentQueueIndex.value = prevIndex;
    _startPlayback(queue.value[prevIndex]);
  }

  function handleTrackEnd() {
    if (currentTrack.value && unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("track naturally ended");
    }

    if (repeatMode.value === "one" && currentTrack.value) {
      currentTime.value = 0;
      _startPlayback(currentTrack.value);
    } else {
      playNextInQueue();
    }
  }

  function setCurrentTime(time: number) {
    currentTime.value = time;
  }
  function setDuration(time: number) {
    duration.value = time;
  }

  function toggleMute() {
    setMuted(!isMutedInternal.value);
  }
  function setRepeatMode(mode: "none" | "one" | "all") {
    repeatMode.value = mode;
  }
  function cycleRepeatMode() {
    if (repeatMode.value === "none") setRepeatMode("all");
    else if (repeatMode.value === "all") setRepeatMode("one");
    else setRepeatMode("none");
  }

  function resetTimes() {
    currentTime.value = 0;
    duration.value = 0;
  }

  function clearQueue() {
    resetPlayerState(false);
  }

  function addTrackToQueue(track: PlayerTrackInfo) {
    const existingTrackIndex = queue.value.findIndex((t) => t.id === track.id);
    if (existingTrackIndex === -1) queue.value.push(track);

    if (!currentTrack.value && queue.value.length > 0) {
      const playIndex = queue.value.findIndex((t) => t.id === track.id);
      currentQueueIndex.value = playIndex !== -1 ? playIndex : 0;
      _startPlayback(queue.value[currentQueueIndex.value]);
    }
  }

  function playTrackFromQueueByIndex(index: number) {
    if (index >= 0 && index < queue.value.length) {
      currentQueueIndex.value = index;
      _startPlayback(queue.value[index]);
    }
  }

  function removeTrackFromQueue(indexToRemove: number) {
    if (indexToRemove < 0 || indexToRemove >= queue.value.length) return;
    const isRemovingCurrentTrack = currentQueueIndex.value === indexToRemove;
    const wasPlaying = isPlaying.value;

    if (
      isRemovingCurrentTrack &&
      currentTrack.value &&
      unmutedSegmentStartTime.value
    ) {
      handleUnmutedSegmentEnd("removed current track from queue");
    }

    queue.value.splice(indexToRemove, 1);

    if (queue.value.length === 0) {
      resetPlayerState(false);
      return;
    }
    if (isRemovingCurrentTrack) {
      let newIndexToPlay = indexToRemove;
      if (newIndexToPlay >= queue.value.length) newIndexToPlay = 0;
      currentQueueIndex.value = newIndexToPlay;
      if (wasPlaying) _startPlayback(queue.value[newIndexToPlay]);
      else {
        currentTrack.value = queue.value[newIndexToPlay];
        currentTrackIdForLogging.value = currentTrack.value.id;
        duration.value = currentTrack.value.duration || 0;
        currentTime.value = 0;
      }
    } else if (indexToRemove < currentQueueIndex.value) {
      currentQueueIndex.value--;
    }
  }

  function resetPlayerState(fullReset = true) {
    if (currentTrack.value && unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("player reset");
    }
    currentTrack.value = null;
    queue.value = [];
    currentQueueIndex.value = -1;
    isPlaying.value = false;
    currentTime.value = 0;
    duration.value = 0;
    currentTrackIdForLogging.value = null;
    unmutedSegmentStartTime.value = null;

    if (fullReset) {
      volumeInternal.value = 0.75;
      isMutedInternal.value = false;
      repeatMode.value = "none";
    }
    localStorage.removeItem(PLAYER_STORAGE_KEY);
    if (fullReset) {
      localStorage.removeItem("playerVolume");
      localStorage.removeItem("playerMuted");
      localStorage.removeItem("playerRepeatMode");
    }
    console.log("Player Store: State reset. Full reset:", fullReset);
  }

  window.addEventListener("beforeunload", () => {
    if (currentTrack.value && unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("window unload");
    }
    if (currentTrack.value && isPlaying.value) {
      clearTimeout(currentTimeSaveTimeout);
      savePlayerStateToLocalStorage({ preservePersistedTime: false });
    } else if (currentTrack.value && !isPlaying.value) {
      savePlayerStateToLocalStorage({ preservePersistedTime: false });
    }
  });

  return {
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    volume,
    isMuted,
    repeatMode,
    queue,
    currentQueueIndex,
    currentTrackUrl,
    currentTrackCoverArtUrl,
    currentTrackDisplayInfo,
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
    playTrackFromQueueByIndex,
    removeTrackFromQueue,
    resetPlayerState,
    handleSeekOperation,
  };
});
