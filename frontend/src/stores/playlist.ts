import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";
import type { Playlist, TrackInfoFromApi } from "@/types";
import { useAuthStore } from "./auth"; // Assuming auth.ts

export interface CreatePlaylistPayload {
  title: string;
  description?: string | null;
  is_public: boolean;
  cover_art?: File | null; // Added for file upload
}

export interface UpdatePlaylistPayload {
  title?: string;
  description?: string | null;
  is_public?: boolean;
  cover_art?: File | null | ""; // Allow File, null (no change), or "" (to remove)
}

export const usePlaylistStore = defineStore("playlist", () => {
  const myPlaylists = ref<Playlist[]>([]);
  const currentPlaylistDetail = ref<Playlist | null>(null);
  const isLoadingMyPlaylists = ref(false);
  const isLoadingPlaylistDetail = ref(false);
  const error = ref<string | null>(null);
  const detailError = ref<string | null>(null);

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

  async function createPlaylist(
    payload: CreatePlaylistPayload
  ): Promise<Playlist | null> {
    if (!authStore.isLoggedIn) {
      error.value = "You must be logged in to create playlists.";
      return null;
    }
    isLoadingMyPlaylists.value = true;
    error.value = null;

    const formData = new FormData();
    formData.append("title", payload.title);
    if (payload.description) {
      formData.append("description", payload.description);
    } else {
      formData.append("description", ""); // Send empty string if null/undefined
    }
    formData.append("is_public", String(payload.is_public));
    if (payload.cover_art) {
      formData.append("cover_art", payload.cover_art);
    }

    try {
      const response = await axios.post<Playlist>("/playlists/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      myPlaylists.value.unshift(response.data);
      return response.data;
    } catch (err) {
      console.error("Playlist Store: Failed to create playlist:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail ||
          Object.values(err.response.data).join(", ") ||
          "Could not create playlist.";
        // Check for specific cover_art GIF error
        if (
          err.response.data.cover_art &&
          Array.isArray(err.response.data.cover_art)
        ) {
          if (
            err.response.data.cover_art.some((e: string) =>
              e.toLowerCase().includes("gif")
            )
          ) {
            error.value += " Animated GIFs are not allowed for cover art.";
          }
        }
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

    const formData = new FormData();
    if (payload.title !== undefined) formData.append("title", payload.title);
    if (payload.description !== undefined)
      formData.append("description", payload.description || "");
    if (payload.is_public !== undefined)
      formData.append("is_public", String(payload.is_public));

    // Handle cover_art:
    // - If payload.cover_art is a File, append it.
    // - If payload.cover_art is an empty string "", it means remove the cover.
    // - If payload.cover_art is null or undefined, do nothing (don't send the field).
    if (payload.cover_art instanceof File) {
      formData.append("cover_art", payload.cover_art);
    } else if (payload.cover_art === "") {
      // Signal to backend to clear the image
      formData.append("cover_art", "");
    }

    try {
      const response = await axios.patch<Playlist>(
        `/playlists/${playlistId}/`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        }
      );
      currentPlaylistDetail.value = response.data;
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
        // Check for specific cover_art GIF error
        if (
          err.response.data.cover_art &&
          Array.isArray(err.response.data.cover_art)
        ) {
          if (
            err.response.data.cover_art.some((e: string) =>
              e.toLowerCase().includes("gif")
            )
          ) {
            detailError.value +=
              " Animated GIFs are not allowed for cover art.";
          }
        }
      } else {
        detailError.value = "An unexpected error occurred.";
      }
      return null;
    } finally {
      isLoadingPlaylistDetail.value = false;
    }
  }

  async function deletePlaylist(playlistId: number): Promise<boolean> {
    isLoadingPlaylistDetail.value = true;
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
      await fetchPlaylistDetail(playlistId); // Refresh the playlist details after adding
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
      await fetchPlaylistDetail(playlistId); // Refresh the playlist details
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
