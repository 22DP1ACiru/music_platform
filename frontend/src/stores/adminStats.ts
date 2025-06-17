import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth";

// Interfaces matching backend AdminDashboardStatsSerializer
interface PlatformSummary {
  total_registered_users: number;
  total_artists: number;
  total_releases: number;
  total_tracks: number;
  total_listen_events: number;
  total_sales_count: number;
  total_sales_value_usd: string; // Decimal as string
}

interface AdminStatsReleaseSummary {
  // Re-using from statsStore for consistency if possible
  id: number;
  title: string;
  cover_art: string | null;
  listen_count: number;
  artist_name: string;
  release_type_display: string;
}

interface AdminStatsTrackSummary {
  // Re-using from statsStore
  id: number;
  title: string;
  listen_count: number;
  duration_in_seconds: number | null;
  release_title: string | null; // Can be null if track is not associated with a release in some edge cases
  artist_name: string | null; // Can be null
  release_id: number | null;
  cover_art: string | null;
}

interface AdminStatsGenreSummary {
  // Re-using from userStatsStore or define specifically
  id: number;
  name: string;
  // If backend adds num_tracks_in_genre or num_listens_in_genre, add here
  // For now, assuming basic GenreSerializer output from music.serializers
  // If 'user_listen_count_for_genre' was a mistake in previous version, adjust here.
  // Let's assume for admin it's about overall popularity, e.g., num_tracks_in_genre
  num_tracks_in_genre?: number; // Example, adjust if backend sends different count
}

export interface AdminPlatformOverviewData {
  platform_summary: PlatformSummary;
  most_popular_releases: AdminStatsReleaseSummary[];
  most_popular_tracks: AdminStatsTrackSummary[];
  most_popular_genres: AdminStatsGenreSummary[];
}

export const useAdminStatsStore = defineStore("adminStats", () => {
  const authStore = useAuthStore();

  const platformOverview = ref<AdminPlatformOverviewData | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchPlatformOverview(
    period: string = "all_time",
    limit: number = 5
  ) {
    if (!authStore.isLoggedIn || !authStore.isStaff) {
      platformOverview.value = null;
      error.value = "You must be an administrator to view these stats.";
      return;
    }

    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get<AdminPlatformOverviewData>(
        `/stats/admin/platform-overview/?period=${period}&limit=${limit}`
      );
      platformOverview.value = response.data;
    } catch (err) {
      console.error("AdminStatsStore: Failed to fetch platform overview:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail || "Could not load platform statistics.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      platformOverview.value = null;
    } finally {
      isLoading.value = false;
    }
  }

  // Clear stats on logout or if user is no longer staff
  authStore.$subscribe((_mutation, state) => {
    if (!state.isLoggedIn || !state.user?.is_staff) {
      platformOverview.value = null;
      isLoading.value = false;
      error.value = null;
    }
  });

  return {
    platformOverview,
    isLoading,
    error,
    fetchPlatformOverview,
  };
});
