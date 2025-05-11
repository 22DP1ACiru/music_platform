import { defineStore } from "pinia";
import { ref, computed } from "vue";

// Interface for track info needed by the player
interface PlayerTrackInfo {
  id: number;
  title: string;
  audio_file: string; // The URL to play
  // Add artist/album later if needed for display
  artistName?: string;
  releaseTitle?: string;
  coverArt?: string | null;
}

export const usePlayerStore = defineStore("player", () => {
  // --- State ---
  const currentTrack = ref<PlayerTrackInfo | null>(null);
  const isPlaying = ref(false);
  // Add queue later: const queue = ref<PlayerTrackInfo[]>([]);
  // Add current time / duration later

  // --- Getters ---
  const currentTrackUrl = computed(
    () => currentTrack.value?.audio_file || null
  );
  const currentTrackDisplayInfo = computed(() => {
    if (!currentTrack.value) return { title: "No track selected", artist: "" };
    return {
      title: currentTrack.value.title,
      artist: currentTrack.value.artistName || "Unknown Artist",
      // cover: currentTrack.value.coverArt
    };
  });

  // --- Actions ---
  function playTrack(track: PlayerTrackInfo) {
    console.log("Player Store: Play track requested", track);
    currentTrack.value = track;
    isPlaying.value = true;
    // Actual playback control happens in the component watching this state
  }

  function pauseTrack() {
    console.log("Player Store: Pause requested");
    isPlaying.value = false;
  }

  function resumeTrack() {
    console.log("Player Store: Resume requested");
    if (currentTrack.value) {
      // Only resume if there's a track loaded
      isPlaying.value = true;
    }
  }

  function togglePlayPause() {
    if (isPlaying.value) {
      pauseTrack();
    } else {
      resumeTrack();
    }
  }

  // Add actions for queue management later

  return {
    // State refs (optional direct exposure)
    // currentTrack,
    // isPlaying,

    // Getters
    currentTrackUrl,
    isPlaying: computed(() => isPlaying.value), // Expose reactive getter
    currentTrackDisplayInfo,

    // Actions
    playTrack,
    pauseTrack,
    resumeTrack,
    togglePlayPause,
  };
});
