import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";
import { useAuthStore } from "./auth";

export const useInteractionsStore = defineStore("interactions", () => {
  const authStore = useAuthStore();

  // Key: artistId, Value: boolean (isFollowing status)
  const followingStatusMap = ref<Record<number, boolean>>({});
  const isLoadingStatus = ref<Record<number, boolean>>({}); // Loading status per artist
  const isLoadingAction = ref<Record<number, boolean>>({}); // Follow/unfollow action loading per artist
  const error = ref<string | null>(null);

  async function checkFollowingStatus(artistId: number): Promise<boolean> {
    if (!authStore.isLoggedIn) {
      followingStatusMap.value[artistId] = false;
      return false;
    }
    isLoadingStatus.value[artistId] = true;
    error.value = null;
    try {
      const response = await axios.get<{ is_following: boolean }>(
        `/interactions/follows/artist/${artistId}/is-following/`
      );
      followingStatusMap.value[artistId] = response.data.is_following;
      return response.data.is_following;
    } catch (err) {
      console.error(
        `InteractionsStore: Failed to check following status for artist ${artistId}:`,
        err
      );
      // Don't set a global error, as this is per-artist.
      // Let the component handle display if needed.
      followingStatusMap.value[artistId] = false; // Assume not following on error
      return false;
    } finally {
      isLoadingStatus.value[artistId] = false;
    }
  }

  async function followArtist(artistId: number): Promise<boolean> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to follow artists.";
      return false;
    }
    isLoadingAction.value[artistId] = true;
    error.value = null;
    try {
      await axios.post("/interactions/follows/follow-artist/", {
        artist_id: artistId,
      });
      followingStatusMap.value[artistId] = true;
      // Consider refetching follower counts or other related data if displayed
      return true;
    } catch (err: any) {
      console.error(
        `InteractionsStore: Failed to follow artist ${artistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).join(", ") ||
          "Could not follow artist.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoadingAction.value[artistId] = false;
    }
  }

  async function unfollowArtist(artistId: number): Promise<boolean> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to unfollow artists.";
      return false;
    }
    isLoadingAction.value[artistId] = true;
    error.value = null;
    try {
      await axios.post("/interactions/follows/unfollow-artist/", {
        artist_id: artistId,
      });
      followingStatusMap.value[artistId] = false;
      // Consider refetching follower counts or other related data
      return true;
    } catch (err: any) {
      console.error(
        `InteractionsStore: Failed to unfollow artist ${artistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).join(", ") ||
          "Could not unfollow artist.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoadingAction.value[artistId] = false;
    }
  }

  function getFollowingStatus(artistId: number): boolean | undefined {
    return followingStatusMap.value[artistId];
  }

  function getIsLoadingStatus(artistId: number): boolean {
    return !!isLoadingStatus.value[artistId];
  }

  function getIsLoadingAction(artistId: number): boolean {
    return !!isLoadingAction.value[artistId];
  }

  // Reset on logout
  authStore.$subscribe((mutation, state) => {
    if (!state.isLoggedIn) {
      followingStatusMap.value = {};
      isLoadingStatus.value = {};
      isLoadingAction.value = {};
      error.value = null;
    }
  });

  return {
    followingStatusMap, // You might not expose this directly if only using getter
    isLoadingStatus, // Same for this
    isLoadingAction, // And this
    error,
    checkFollowingStatus,
    followArtist,
    unfollowArtist,
    getFollowingStatus, // Getter function
    getIsLoadingStatus,
    getIsLoadingAction,
  };
});
