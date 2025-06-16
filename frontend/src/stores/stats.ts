import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth"; // To ensure user is logged in and an artist

// Define interfaces for the expected stats data structure
// These should match your backend serializers
interface ArtistBasicStats {
  total_release_listens: number;
  total_track_listens: number;
  total_sales_count: number;
  total_sales_value_usd: string; // Assuming string from backend for decimal
  current_follower_count: number;
}

interface StatsReleaseSummary {
  id: number;
  title: string;
  cover_art: string | null;
  listen_count: number;
  artist_name: string; // Or ArtistInfo object
  release_type_display: string;
}

interface StatsTrackSummary {
  id: number;
  title: string;
  listen_count: number;
  duration_in_seconds: number | null;
  release_title: string;
  artist_name: string;
}

export interface ArtistDashboardData {
  summary: ArtistBasicStats;
  top_releases: StatsReleaseSummary[];
  top_tracks: StatsTrackSummary[];
}

export const useStatsStore = defineStore("stats", () => {
  const authStore = useAuthStore();

  const artistDashboardStats = ref<ArtistDashboardData | null>(null);
  const isLoadingArtistStats = ref(false);
  const errorArtistStats = ref<string | null>(null);

  async function fetchArtistDashboardStats(period: string = "all_time") {
    if (!authStore.isLoggedIn || !authStore.hasArtistProfile) {
      artistDashboardStats.value = null;
      errorArtistStats.value = "You must be an artist to view these stats.";
      return;
    }

    isLoadingArtistStats.value = true;
    errorArtistStats.value = null;
    try {
      const response = await axios.get<ArtistDashboardData>(
        `/stats/artist/my-dashboard/?period=${period}`
      );
      artistDashboardStats.value = response.data;
    } catch (err) {
      console.error("StatsStore: Failed to fetch artist dashboard stats:", err);
      if (axios.isAxiosError(err) && err.response) {
        errorArtistStats.value =
          err.response.data.detail || "Could not load artist statistics.";
      } else {
        errorArtistStats.value = "An unexpected error occurred.";
      }
      artistDashboardStats.value = null;
    } finally {
      isLoadingArtistStats.value = false;
    }
  }

  // Clear stats on logout
  authStore.$subscribe((_mutation, state) => {
    if (!state.isLoggedIn) {
      artistDashboardStats.value = null;
      isLoadingArtistStats.value = false;
      errorArtistStats.value = null;
    }
  });

  return {
    artistDashboardStats,
    isLoadingArtistStats,
    errorArtistStats,
    fetchArtistDashboardStats,
  };
});
