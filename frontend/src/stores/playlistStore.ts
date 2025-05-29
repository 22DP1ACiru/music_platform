import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";
import type { Playlist, TrackInfoFromApi } from "@/types"; // Added TrackInfoFromApi
import { useAuthStore } from "./auth";

export interface UpdatePlaylistPayload {
  title?: string;
  description?: string | null;
  is_public?: boolean;
  // cover_art might be handled separately if it involves file upload
}

export const usePlaylistStore = defineStore("playlist", () => {
  const myPlaylists = ref<Playlist[]>([]);
  const currentPlaylistDetail = ref<Playlist | null>(null);
  const isLoadingMyPlaylists = ref(false);
  const isLoadingPlaylistDetail = ref(false);
  const error = ref<string | null>(null);
  const detailError = ref<string | null>(null); // For errors on detail page

  const authStore = useAuthStore();

  async function fetchMyPlaylists() {
    if (!authStore.isLoggedIn) {
      myPlaylists.value = [];
      return;
    }
    isLoadingMyPlaylists.value = true;
    error.value = null;
    try {
      const response = await axios.get<{ results: Playlist[] }>("/playlists/");
      if (authStore.authUser) {
        myPlaylists.value = response.data.results.filter(
          (p) => p.owner === authStore.authUser?.username
        );
      } else {
        myPlaylists.value = [];
      }
    } catch (err) {
      console.error("Playlist Store: Failed to fetch playlists:", err);
      error.value = "Could not load your playlists.";
      myPlaylists.value = [];
    } finally {
      isLoadingMyPlaylists.value = false;
    }
  }

  async function createPlaylist(payload: {
    title: string;
    description?: string | null;
    is_public: boolean;
  }): Promise<Playlist | null> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to create playlists.";
      return null;
    }
    isLoadingMyPlaylists.value = true; // Or a specific isLoadingCreate
    error.value = null;
    try {
      const response = await axios.post<Playlist>("/playlists/", payload);
      myPlaylists.value.unshift(response.data);
      return response.data;
    } catch (err) {
      console.error("Playlist Store: Failed to create playlist:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).join(", ") ||
          "Could not create playlist.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return null;
    } finally {
      isLoadingMyPlaylists.value = false;
    }
  }

  async function fetchPlaylistDetail(playlistId: number | string) {
    isLoadingPlaylistDetail.value = true;
    detailError.value = null;
    currentPlaylistDetail.value = null;
    try {
      const response = await axios.get<Playlist>(`/playlists/${playlistId}/`);
      currentPlaylistDetail.value = response.data;
    } catch (err) {
      console.error(
        `Playlist Store: Failed to fetch playlist detail ${playlistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        detailError.value = "Playlist not found.";
      } else {
        detailError.value = "Could not load playlist details.";
      }
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  async function updatePlaylist(
    playlistId: number,
    payload: UpdatePlaylistPayload
  ): Promise<Playlist | null> {
    isLoadingPlaylistDetail.value = true;
    detailError.value = null;
    try {
      const response = await axios.patch<Playlist>(
        `/playlists/${playlistId}/`,
        payload
      );
      currentPlaylistDetail.value = response.data;
      // Update in the main list as well
      const index = myPlaylists.value.findIndex((p) => p.id === playlistId);
      if (index !== -1) {
        myPlaylists.value[index] = response.data;
      }
      return response.data;
    } catch (err) {
      console.error(
        `Playlist Store: Failed to update playlist ${playlistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        detailError.value =
          err.response.data.detail ||
          Object.values(err.response.data).join(", ") ||
          "Could not update playlist.";
      } else {
        detailError.value = "An unexpected error occurred.";
      }
      return null;
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  async function deletePlaylist(playlistId: number): Promise<boolean> {
    isLoadingPlaylistDetail.value = true; // Use detail loading for context
    detailError.value = null;
    try {
      await axios.delete(`/playlists/${playlistId}/`);
      myPlaylists.value = myPlaylists.value.filter((p) => p.id !== playlistId);
      if (currentPlaylistDetail.value?.id === playlistId) {
        currentPlaylistDetail.value = null;
      }
      return true;
    } catch (err) {
      console.error(
        `Playlist Store: Failed to delete playlist ${playlistId}:`,
        err
      );
      detailError.value = "Could not delete playlist.";
      return false;
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  async function addTrackToPlaylist(
    playlistId: number,
    trackId: number
  ): Promise<boolean> {
    isLoadingPlaylistDetail.value = true;
    detailError.value = null;
    try {
      await axios.post(`/playlists/${playlistId}/add_track/`, {
        track_id: trackId,
      });
      // Re-fetch details to get updated track list and count
      await fetchPlaylistDetail(playlistId);
      // Also update the track_count in the main list if it's there
      const index = myPlaylists.value.findIndex((p) => p.id === playlistId);
      if (index !== -1 && currentPlaylistDetail.value) {
        myPlaylists.value[index].track_count =
          currentPlaylistDetail.value.track_count;
      }
      return true;
    } catch (err) {
      console.error(
        `Playlist Store: Failed to add track ${trackId} to playlist ${playlistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        const errorData = err.response.data;
        if (
          typeof errorData === "object" &&
          errorData !== null &&
          "error" in errorData
        ) {
          detailError.value = (errorData as any).error;
        } else if (
          typeof errorData === "object" &&
          errorData !== null &&
          "detail" in errorData
        ) {
          detailError.value = (errorData as any).detail;
        } else {
          detailError.value = "Could not add track to playlist.";
        }
      } else {
        detailError.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  async function removeTrackFromPlaylist(
    playlistId: number,
    trackId: number
  ): Promise<boolean> {
    isLoadingPlaylistDetail.value = true;
    detailError.value = null;
    try {
      await axios.post(`/playlists/${playlistId}/remove_track/`, {
        track_id: trackId,
      });
      // Re-fetch details
      await fetchPlaylistDetail(playlistId);
      const index = myPlaylists.value.findIndex((p) => p.id === playlistId);
      if (index !== -1 && currentPlaylistDetail.value) {
        myPlaylists.value[index].track_count =
          currentPlaylistDetail.value.track_count;
      }
      return true;
    } catch (err) {
      console.error(
        `Playlist Store: Failed to remove track ${trackId} from playlist ${playlistId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        const errorData = err.response.data;
        if (
          typeof errorData === "object" &&
          errorData !== null &&
          "error" in errorData
        ) {
          detailError.value = (errorData as any).error;
        } else if (
          typeof errorData === "object" &&
          errorData !== null &&
          "detail" in errorData
        ) {
          detailError.value = (errorData as any).detail;
        } else {
          detailError.value = "Could not remove track from playlist.";
        }
      } else {
        detailError.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  return {
    myPlaylists,
    currentPlaylistDetail,
    isLoadingMyPlaylists,
    isLoadingPlaylistDetail,
    error,
    detailError,
    fetchMyPlaylists,
    createPlaylist,
    fetchPlaylistDetail,
    updatePlaylist,
    deletePlaylist,
    addTrackToPlaylist,
    removeTrackFromPlaylist,
  };
});
