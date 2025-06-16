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
  persistedIsShuffleActive?: boolean; // Added for shuffle persistence
}

const PLAYER_STORAGE_KEY = "vaultwavePlayerState";
const MIN_LOGGABLE_SEGMENT_MS = 2000;

export const usePlayerStore = defineStore("player", () => {
  const authStore = useAuthStore();

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
      persistedIsShuffleActive: false,
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

  const isShuffleActive = ref<boolean>(
    initialState.persistedIsShuffleActive ?? false
  );
  const shuffledPlayOrderIndices = ref<number[]>([]);
  const currentShuffledOrderIndex = ref<number>(-1);

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

  const canShuffle = computed(() => queue.value.length >= 3);

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
      persistedIsShuffleActive: isShuffleActive.value,
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
    if (!authStore.isLoggedIn) {
      return;
    }
    if (segmentDurationMs < MIN_LOGGABLE_SEGMENT_MS) {
      return;
    }
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
      logListenSegment(
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
      unmutedSegmentStartTime.value = Date.now();
      currentTrackIdForLogging.value = currentTrack.value.id;
    } else {
      unmutedSegmentStartTime.value = null;
      currentTrackIdForLogging.value = currentTrack.value?.id || null;
    }
  }

  function handleSeekOperation() {
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
    (newTrack) => {
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
    [queue, currentQueueIndex, isShuffleActive],
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
      !isShuffleActive.value &&
      (currentQueueIndex.value === -1 ||
        queue.value[currentQueueIndex.value]?.id !== track.id)
    ) {
      currentTime.value = 0;
    } else if (
      isShuffleActive.value &&
      (oldTrackId !== track.id || currentTime.value === duration.value)
    ) {
      currentTime.value = 0;
    }
    isPlaying.value = true;
    if (isEffectivelyAudible.value) {
      handleUnmutedSegmentStart();
    }
  }

  function _generateShuffledIndices(length: number): number[] {
    const indices = Array.from({ length }, (_, i) => i);
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [indices[i], indices[j]] = [indices[j], indices[i]];
    }
    return indices;
  }

  function toggleShuffle() {
    if (!canShuffle.value && !isShuffleActive.value) {
      return;
    }
    isShuffleActive.value = !isShuffleActive.value;
    if (isShuffleActive.value) {
      shuffledPlayOrderIndices.value = _generateShuffledIndices(
        queue.value.length
      );
      currentShuffledOrderIndex.value = -1;
      if (currentTrack.value && currentQueueIndex.value !== -1) {
        const currentTrackOriginalIndex = currentQueueIndex.value;
        const newPosInShuffled = shuffledPlayOrderIndices.value.indexOf(
          currentTrackOriginalIndex
        );
        if (newPosInShuffled !== -1) {
          shuffledPlayOrderIndices.value.splice(newPosInShuffled, 1);
          shuffledPlayOrderIndices.value.unshift(currentTrackOriginalIndex);
          currentShuffledOrderIndex.value = 0; // Set after unshift
        }
      }
    } else {
      shuffledPlayOrderIndices.value = [];
      currentShuffledOrderIndex.value = -1;
    }
    savePlayerStateToLocalStorage();
  }

  function setQueueAndPlay(tracks: PlayerTrackInfo[], startIndex: number = 0) {
    if (!tracks || tracks.length === 0) {
      resetPlayerState(false);
      return;
    }
    if (startIndex < 0 || startIndex >= tracks.length) startIndex = 0;
    queue.value = [...tracks];
    currentQueueIndex.value = startIndex;
    if (isShuffleActive.value) {
      if (queue.value.length < 3) {
        isShuffleActive.value = false;
        shuffledPlayOrderIndices.value = [];
        currentShuffledOrderIndex.value = -1;
      } else {
        shuffledPlayOrderIndices.value = _generateShuffledIndices(
          queue.value.length
        );
        const newPosInShuffled =
          shuffledPlayOrderIndices.value.indexOf(startIndex);
        if (newPosInShuffled !== -1) {
          shuffledPlayOrderIndices.value.splice(newPosInShuffled, 1);
          shuffledPlayOrderIndices.value.unshift(startIndex);
        }
        currentShuffledOrderIndex.value = 0;
        _startPlayback(queue.value[shuffledPlayOrderIndices.value[0]]);
        return;
      }
    }
    _startPlayback(queue.value[startIndex]);
  }

  function playTrack(track: PlayerTrackInfo) {
    if (isShuffleActive.value) toggleShuffle();
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
      if (isShuffleActive.value) {
        if (shuffledPlayOrderIndices.value.length > 0) {
          currentShuffledOrderIndex.value =
            (currentShuffledOrderIndex.value + 1) %
            shuffledPlayOrderIndices.value.length;
          const nextOriginalIndex =
            shuffledPlayOrderIndices.value[currentShuffledOrderIndex.value];
          currentQueueIndex.value = nextOriginalIndex;
          _startPlayback(queue.value[nextOriginalIndex]);
        } else {
          toggleShuffle();
          if (shuffledPlayOrderIndices.value.length > 0) playNextInQueue();
        }
      } else {
        const indexToPlay =
          currentQueueIndex.value !== -1 &&
          currentQueueIndex.value < queue.value.length
            ? currentQueueIndex.value
            : 0;
        if (indexToPlay < queue.value.length) {
          currentQueueIndex.value = indexToPlay;
          _startPlayback(queue.value[indexToPlay]);
        }
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

    if (isShuffleActive.value) {
      if (shuffledPlayOrderIndices.value.length === 0) {
        toggleShuffle();
        if (shuffledPlayOrderIndices.value.length === 0) {
          isPlaying.value = false;
          return;
        }
      }
      currentShuffledOrderIndex.value++;
      if (
        currentShuffledOrderIndex.value >= shuffledPlayOrderIndices.value.length
      ) {
        // If shuffle is on, and it's not repeat-one (which handleTrackEnd deals with), then loop the shuffle.
        shuffledPlayOrderIndices.value = _generateShuffledIndices(
          queue.value.length
        );
        currentShuffledOrderIndex.value = 0;
        if (
          queue.value.length > 1 &&
          currentTrack.value &&
          queue.value[shuffledPlayOrderIndices.value[0]].id ===
            currentTrack.value.id
        ) {
          currentShuffledOrderIndex.value =
            1 % shuffledPlayOrderIndices.value.length;
        }
      }
      const nextOriginalIndex =
        shuffledPlayOrderIndices.value[currentShuffledOrderIndex.value];
      currentQueueIndex.value = nextOriginalIndex;
      _startPlayback(queue.value[nextOriginalIndex]);
    } else {
      // Sequential playback
      let nextIndex = currentQueueIndex.value + 1;
      if (nextIndex >= queue.value.length) {
        if (repeatMode.value === "all") {
          nextIndex = 0;
        } else {
          // repeatMode is 'none' (or 'one' but handled by handleTrackEnd)
          if (unmutedSegmentStartTime.value)
            handleUnmutedSegmentEnd(
              "sequential queue ended, no repeat all/one"
            );
          isPlaying.value = false;
          if (duration.value > 0) currentTime.value = duration.value;
          return;
        }
      }
      currentQueueIndex.value = nextIndex;
      _startPlayback(queue.value[nextIndex]);
    }
  }

  function playPreviousInQueue() {
    if (queue.value.length === 0) return;
    if (isShuffleActive.value) {
      if (shuffledPlayOrderIndices.value.length === 0) {
        toggleShuffle();
        if (shuffledPlayOrderIndices.value.length === 0) return;
      }
      currentShuffledOrderIndex.value--;
      if (currentShuffledOrderIndex.value < 0) {
        // For shuffle, "previous" when at the start of a shuffled list can mean end of *current* shuffle, or re-shuffle.
        // Let's go to the end of the current shuffled list to act like a loop.
        currentShuffledOrderIndex.value =
          shuffledPlayOrderIndices.value.length - 1;
        // Or, if you want it to re-shuffle and pick a "random previous":
        // shuffledPlayOrderIndices.value = _generateShuffledIndices(queue.value.length);
        // currentShuffledOrderIndex.value = shuffledPlayOrderIndices.value.length -1;
      }
      const prevOriginalIndex =
        shuffledPlayOrderIndices.value[currentShuffledOrderIndex.value];
      currentQueueIndex.value = prevOriginalIndex;
      _startPlayback(queue.value[prevOriginalIndex]);
    } else {
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
        )
          handleUnmutedSegmentEnd("replay current track");
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
            )
              handleUnmutedSegmentEnd("replay current track at start of queue");
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
    isShuffleActive.value = false;
    shuffledPlayOrderIndices.value = [];
    currentShuffledOrderIndex.value = -1;
    resetPlayerState(false);
  }

  function addTrackToQueue(track: PlayerTrackInfo) {
    const existingTrackIndex = queue.value.findIndex((t) => t.id === track.id);
    if (existingTrackIndex === -1) {
      queue.value.push(track);
      if (isShuffleActive.value && queue.value.length >= 3) {
        const currentPlayingOriginalIndex = currentTrack.value
          ? queue.value.findIndex((t) => t.id === currentTrack.value!.id)
          : -1;
        shuffledPlayOrderIndices.value = _generateShuffledIndices(
          queue.value.length
        );
        if (currentPlayingOriginalIndex !== -1) {
          const newPos = shuffledPlayOrderIndices.value.indexOf(
            currentPlayingOriginalIndex
          );
          if (newPos !== -1) {
            shuffledPlayOrderIndices.value.splice(newPos, 1);
            shuffledPlayOrderIndices.value.unshift(currentPlayingOriginalIndex);
            currentShuffledOrderIndex.value = 0;
          } else {
            currentShuffledOrderIndex.value = -1;
          }
        } else {
          currentShuffledOrderIndex.value = -1;
        }
      } else if (queue.value.length >= 3 && !isShuffleActive.value) {
        /* Do nothing to shuffle state */
      } else if (queue.value.length < 3 && isShuffleActive.value) {
        isShuffleActive.value = false;
        shuffledPlayOrderIndices.value = [];
        currentShuffledOrderIndex.value = -1;
      }
    }
    if (!currentTrack.value && queue.value.length > 0) {
      if (isShuffleActive.value && shuffledPlayOrderIndices.value.length > 0) {
        currentShuffledOrderIndex.value = 0;
        const originalIndex = shuffledPlayOrderIndices.value[0];
        currentQueueIndex.value = originalIndex;
        _startPlayback(queue.value[originalIndex]);
      } else {
        currentQueueIndex.value = queue.value.length - 1;
        _startPlayback(queue.value[currentQueueIndex.value]);
      }
    }
  }

  function playTrackFromQueueByIndex(index: number) {
    if (isShuffleActive.value) toggleShuffle();
    if (index >= 0 && index < queue.value.length) {
      currentQueueIndex.value = index;
      _startPlayback(queue.value[index]);
    }
  }

  function removeTrackFromQueue(indexToRemove: number) {
    if (indexToRemove < 0 || indexToRemove >= queue.value.length) return;
    const removedTrackOriginalId = queue.value[indexToRemove].id;
    const isRemovingCurrentTrack =
      currentTrack.value?.id === removedTrackOriginalId;
    const wasPlaying = isPlaying.value;
    if (isRemovingCurrentTrack && unmutedSegmentStartTime.value) {
      handleUnmutedSegmentEnd("removed current track from queue");
    }
    queue.value.splice(indexToRemove, 1);
    if (isShuffleActive.value) {
      if (queue.value.length < 3) {
        isShuffleActive.value = false;
        shuffledPlayOrderIndices.value = [];
        currentShuffledOrderIndex.value = -1;
        if (currentTrack.value) {
          const newIdx = queue.value.findIndex(
            (t) => t.id === currentTrack.value!.id
          );
          currentQueueIndex.value = newIdx;
          if (newIdx === -1 && queue.value.length > 0) {
            currentQueueIndex.value = 0;
            if (wasPlaying) _startPlayback(queue.value[0]);
            else currentTrack.value = queue.value[0];
          } else if (newIdx === -1 && queue.value.length === 0) {
            resetPlayerState(false);
          }
        } else if (queue.value.length > 0) {
          currentQueueIndex.value = 0;
        } else {
          resetPlayerState(false);
        }
      } else {
        const currentPlayingOriginalIndexAfterRemove = currentTrack.value
          ? queue.value.findIndex((t) => t.id === currentTrack.value!.id)
          : -1;
        shuffledPlayOrderIndices.value = _generateShuffledIndices(
          queue.value.length
        );
        if (currentPlayingOriginalIndexAfterRemove !== -1) {
          const newPos = shuffledPlayOrderIndices.value.indexOf(
            currentPlayingOriginalIndexAfterRemove
          );
          if (newPos !== -1) {
            shuffledPlayOrderIndices.value.splice(newPos, 1);
            shuffledPlayOrderIndices.value.unshift(
              currentPlayingOriginalIndexAfterRemove
            );
            currentShuffledOrderIndex.value = 0;
          } else {
            currentShuffledOrderIndex.value = -1;
          }
        } else {
          currentShuffledOrderIndex.value = -1;
          if (isRemovingCurrentTrack && queue.value.length > 0 && wasPlaying) {
            currentShuffledOrderIndex.value = 0;
            const nextOriginalIndex = shuffledPlayOrderIndices.value[0];
            currentQueueIndex.value = nextOriginalIndex;
            _startPlayback(queue.value[nextOriginalIndex]);
          } else if (isRemovingCurrentTrack && queue.value.length === 0) {
            resetPlayerState(false);
          }
        }
      }
    } else {
      if (isRemovingCurrentTrack) {
        if (queue.value.length === 0) {
          resetPlayerState(false);
          return;
        }
        let newIndexToPlay = indexToRemove;
        if (newIndexToPlay >= queue.value.length) newIndexToPlay = 0;
        currentQueueIndex.value = newIndexToPlay;
        if (wasPlaying) _startPlayback(queue.value[newIndexToPlay]);
        else {
          currentTrack.value = queue.value[newIndexToPlay];
          duration.value = currentTrack.value.duration || 0;
          currentTime.value = 0;
        }
      } else if (indexToRemove < currentQueueIndex.value) {
        currentQueueIndex.value--;
      }
    }
    savePlayerStateToLocalStorage();
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
    isShuffleActive.value = false;
    shuffledPlayOrderIndices.value = [];
    currentShuffledOrderIndex.value = -1;
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
    isShuffleActive,
    canShuffle,
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
    toggleShuffle,
  };
});
