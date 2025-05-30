import { defineStore } from "pinia";
import { ref, computed, watch } from "vue";
import type { PlayerTrackInfo } from "@/types";
import axios from "axios";

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
const MIN_LOGGABLE_SEGMENT_MS = 2000; // Minimum segment duration in milliseconds to log

export const usePlayerStore = defineStore("player", () => {
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

  const volume = ref<number>(initialState.persistedVolume ?? 0.75);
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
      persistedVolume: volume.value,
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
    if (segmentDurationMs < MIN_LOGGABLE_SEGMENT_MS) {
      // Use the constant
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
        currentTrackIdForLogging.value,
        unmutedSegmentStartTime.value,
        durationMs
      );
    }
    unmutedSegmentStartTime.value = null;
  }

  function handleUnmutedSegmentStart() {
    if (
      isPlaying.value &&
      !isMutedInternal.value &&
      currentTrack.value &&
      currentTrack.value.id
    ) {
      console.log(
        `PlayerStore: New unmuted segment started for track ${currentTrack.value.id}.`
      );
      unmutedSegmentStartTime.value = Date.now();
      currentTrackIdForLogging.value = currentTrack.value.id;
    } else {
      if (unmutedSegmentStartTime.value) {
        console.log(
          "PlayerStore: Conditions not met for new unmuted segment, ending any previous one."
        );
        handleUnmutedSegmentEnd("conditions not met for start");
      }
      currentTrackIdForLogging.value = currentTrack.value?.id || null;
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
      if (oldTrack && oldTrack.id) {
        handleUnmutedSegmentEnd("track changed");
      }
      currentTrackIdForLogging.value = newTrack?.id || null;
      if (newTrack) {
      } else {
        unmutedSegmentStartTime.value = null;
      }
      savePlayerStateToLocalStorage({ preservePersistedTime: !newTrack });
    },
    { deep: true }
  );

  watch(isPlaying, (playing, wasPlaying) => {
    if (currentTrack.value) {
      if (playing && !isMutedInternal.value) {
        handleUnmutedSegmentStart();
      } else if (!playing && unmutedSegmentStartTime.value) {
        handleUnmutedSegmentEnd(
          playing ? "became muted while playing (unexpected)" : "paused/stopped"
        );
      }
    }
    if (!playing && currentTrack.value) {
      clearTimeout(currentTimeSaveTimeout);
      savePlayerStateToLocalStorage({ preservePersistedTime: false });
    } else {
      savePlayerStateToLocalStorage({ preservePersistedTime: true });
    }
  });

  function setMuted(muted: boolean) {
    const oldMuteState = isMutedInternal.value;
    isMutedInternal.value = muted;

    if (oldMuteState !== muted && currentTrack.value && isPlaying.value) {
      if (muted) {
        handleUnmutedSegmentEnd("muted");
      } else {
        handleUnmutedSegmentStart();
      }
    }
    savePlayerStateToLocalStorage({ preservePersistedTime: true });
  }

  watch(
    [queue, currentQueueIndex],
    () => {
      savePlayerStateToLocalStorage({ preservePersistedTime: true });
    },
    { deep: true }
  );

  watch([volume, repeatMode], () => {
    savePlayerStateToLocalStorage({ preservePersistedTime: true });
  });

  function _startPlayback(track: PlayerTrackInfo) {
    currentTrack.value = track;
    if (
      currentQueueIndex.value !== -1 &&
      queue.value[currentQueueIndex.value]?.id === track.id
    ) {
    } else {
      currentTime.value = 0;
    }
    isPlaying.value = true;
  }

  function setQueueAndPlay(tracks: PlayerTrackInfo[], startIndex: number = 0) {
    if (!tracks || tracks.length === 0) {
      resetPlayerState(false);
      return;
    }
    if (startIndex < 0 || startIndex >= tracks.length) startIndex = 0;

    queue.value = [...tracks];
    currentQueueIndex.value = startIndex;
    currentTime.value = 0;
    _startPlayback(queue.value[startIndex]);
  }

  function playTrack(track: PlayerTrackInfo) {
    currentTime.value = 0;
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
        currentTime.value = 0;
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
        isPlaying.value = false;
        if (duration.value > 0) currentTime.value = duration.value;
        return;
      }
    }
    currentQueueIndex.value = nextIndex;
    currentTime.value = 0;
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
      currentTime.value = 0;
      if (currentTrack.value) {
        isPlaying.value = true;
      }
      return;
    }
    let prevIndex = currentQueueIndex.value - 1;
    if (prevIndex < 0) {
      if (repeatMode.value === "all") {
        prevIndex = queue.value.length - 1;
      } else {
        if (currentTrack.value) {
          currentTime.value = 0;
          isPlaying.value = true;
        }
        return;
      }
    }
    currentQueueIndex.value = prevIndex;
    currentTime.value = 0;
    _startPlayback(queue.value[prevIndex]);
  }

  function handleTrackEnd() {
    if (repeatMode.value === "one" && currentTrack.value) {
      currentTime.value = 0;
      isPlaying.value = true;
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
  function setVolume(vol: number) {
    volume.value = Math.max(0, Math.min(1, vol));
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
      currentTime.value = 0;
      _startPlayback(queue.value[index]);
    }
  }

  function removeTrackFromQueue(indexToRemove: number) {
    if (indexToRemove < 0 || indexToRemove >= queue.value.length) return;
    const isRemovingCurrentTrack = currentQueueIndex.value === indexToRemove;
    const wasPlaying = isPlaying.value;

    queue.value.splice(indexToRemove, 1);

    if (queue.value.length === 0) {
      resetPlayerState(false);
      return;
    }
    if (isRemovingCurrentTrack) {
      let newIndexToPlay = indexToRemove;
      if (newIndexToPlay >= queue.value.length) newIndexToPlay = 0;
      currentQueueIndex.value = newIndexToPlay;
      currentTime.value = 0;
      if (wasPlaying) _startPlayback(queue.value[newIndexToPlay]);
      else {
        currentTrack.value = queue.value[newIndexToPlay];
        duration.value = currentTrack.value.duration || 0;
      }
    } else if (indexToRemove < currentQueueIndex.value) {
      currentQueueIndex.value--;
    }
  }

  function resetPlayerState(fullReset = true) {
    if (currentTrack.value) {
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
      volume.value = 0.75;
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
    if (currentTrack.value) {
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
  };
});
