import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth"; // To ensure user is logged in

// Interfaces to match the backend UserListeningHabitsSerializer output
export interface UserListenedTrack {
  id: number;
  title: string;
  duration_in_seconds: number | null;
  release_title: string | null;
  artist_name: string | null;
  artist_id: number | null;
  release_id: number | null;
  cover_art: string | null; // This will be a relative path
  user_listen_count: number;
}

export interface UserListenedArtist {
  id: number;
  name: string;
  artist_picture: string | null; // This will be a relative path
  user_listen_count_for_artist: number;
}

export interface UserListenedGenre {
  id: number;
  name: string;
  user_listen_count_for_genre: number;
}

export interface UserListeningHabitsData {
  top_listened_tracks: UserListenedTrack[];
  top_listened_artists: UserListenedArtist[];
  top_listened_genres: UserListenedGenre[];
  total_listen_events_count: number;
}

export const useUserStatsStore = defineStore("userStats", () => {
  const authStore = useAuthStore();

  const listeningHabits = ref<UserListeningHabitsData | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchMyListeningHabits(
    period: string = "all_time",
    limit: number = 5
  ) {
    if (!authStore.isLoggedIn) {
      listeningHabits.value = null;
      error.value = "You must be logged in to view your listening habits.";
      return;
    }

    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get<UserListeningHabitsData>(
        `/stats/user/my-listening-habits/?period=${period}&limit=${limit}`
      );
      listeningHabits.value = response.data;
    } catch (err) {
      console.error("UserStatsStore: Failed to fetch listening habits:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail || "Could not load your listening habits.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      listeningHabits.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  // Clear stats on logout
  authStore.$subscribe((_mutation, state) => {
    if (!state.isLoggedIn) {
      listeningHabits.value = null;
      isLoading.value = false;
      error.value = null;
    }
  });

  return {
    listeningHabits,
    isLoading,
    error,
    fetchMyListeningHabits,
  };
});
