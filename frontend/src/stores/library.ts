import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { ReleaseDetail, GeneratedDownloadStatus } from "@/types"; // Import from new types file

export interface LibraryItem {
  id: number;
  user: string; // username
  release: ReleaseDetail; // Nested release data
  acquired_at: string;
  acquisition_type: "FREE" | "PURCHASED" | "NYP";
}

export const useLibraryStore = defineStore("library", () => {
  const libraryItems = ref<LibraryItem[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  const activeDownloadRequests = ref<
    Record<number, GeneratedDownloadStatus | null>
  >({});
  const activeDownloadErrors = ref<Record<number, string | null>>({});
  const isProcessingDownload = ref<Record<number, boolean>>({});

  const getLibraryItemByReleaseId = computed(() => {
    return (releaseId: number) =>
      libraryItems.value.find((item) => item.release.id === releaseId);
  });

  async function fetchLibraryItems() {
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.get<LibraryItem[]>("/library/");
      libraryItems.value = response.data;
    } catch (err) {
      console.error("Library Store: Failed to fetch library items:", err);
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        error.value = "Please log in to view your library.";
      } else {
        error.value = "Could not load your library.";
      }
      libraryItems.value = [];
    } finally {
      isLoading.value = false;
    }
  }

  async function addItemToLibrary(
    releaseId: number,
    acquisitionType: "FREE" | "PAID" | "NYP"
  ) {
    if (getLibraryItemByReleaseId.value(releaseId)) {
      console.log("Library Store: Item already in library.");
      return true;
    }
    isLoading.value = true;
    error.value = null;
    try {
      const response = await axios.post<LibraryItem>("/library/add-item/", {
        release_id: releaseId,
        acquisition_type: acquisitionType,
      });
      libraryItems.value.unshift(response.data);
      return true;
    } catch (err) {
      console.error("Library Store: Failed to add item to library:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail || "Could not add item to library.";
      } else {
        error.value = "An unexpected error occurred.";
      }
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  async function removeItemFromLibrary(libraryItemId: number) {
    isLoading.value = true;
    error.value = null;
    try {
      await axios.delete(`/library/${libraryItemId}/remove-item/`);
      libraryItems.value = libraryItems.value.filter(
        (item) => item.id !== libraryItemId
      );
      delete activeDownloadRequests.value[libraryItemId];
      delete activeDownloadErrors.value[libraryItemId];
      delete isProcessingDownload.value[libraryItemId];
    } catch (err) {
      console.error("Library Store: Failed to remove item from library:", err);
      if (axios.isAxiosError(err) && err.response) {
        error.value =
          err.response.data.detail || "Could not remove item from library.";
      } else {
        error.value = "An unexpected error occurred.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function requestLibraryItemDownload(
    libraryItemId: number,
    requestedFormat: string
  ) {
    isProcessingDownload.value[libraryItemId] = true;
    activeDownloadErrors.value[libraryItemId] = null;
    activeDownloadRequests.value[libraryItemId] = null;

    try {
      const response = await axios.post<GeneratedDownloadStatus>(
        `/library/${libraryItemId}/request-download/`,
        { requested_format: requestedFormat }
      );
      activeDownloadRequests.value[libraryItemId] = response.data;
      if (
        response.data.status === "PENDING" ||
        response.data.status === "PROCESSING"
      ) {
        startPollingForLibraryItem(libraryItemId, response.data.id); // Pass GeneratedDownload.id
      }
    } catch (err) {
      console.error(
        `Library Store: Failed to request download for library item ${libraryItemId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        activeDownloadErrors.value[libraryItemId] =
          err.response.data.detail || "Failed to start download preparation.";
      } else {
        activeDownloadErrors.value[libraryItemId] =
          "An unexpected error occurred.";
      }
    } finally {
      isProcessingDownload.value[libraryItemId] = false;
    }
  }

  const pollingIntervals: Record<number, number | undefined> = {};

  async function pollSpecificDownloadStatus(
    libraryItemId: number, // This is UserLibraryItem.id, used as a key for UI state
    downloadInstanceId: number // This is GeneratedDownload.id, used for API calls
  ) {
    try {
      const response = await axios.get<GeneratedDownloadStatus>(
        `/generated-download-status/${downloadInstanceId}/`
      );
      activeDownloadRequests.value[libraryItemId] = response.data;

      if (
        response.data.status === "READY" ||
        response.data.status === "FAILED" ||
        response.data.status === "EXPIRED"
      ) {
        stopPollingForLibraryItem(libraryItemId);
      }
    } catch (err) {
      console.error(
        `Library Store: Polling error for download ${downloadInstanceId} of library item ${libraryItemId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        activeDownloadErrors.value[libraryItemId] =
          "Download request not found during polling.";
      } else {
        activeDownloadErrors.value[libraryItemId] =
          "Error checking download status during polling.";
      }
      stopPollingForLibraryItem(libraryItemId);
    }
  }

  function startPollingForLibraryItem(
    libraryItemId: number,
    downloadInstanceId: number // GeneratedDownload.id
  ) {
    stopPollingForLibraryItem(libraryItemId);
    pollSpecificDownloadStatus(libraryItemId, downloadInstanceId); // Initial poll
    pollingIntervals[libraryItemId] = window.setInterval(() => {
      // Use downloadInstanceId for subsequent polls as it refers to the specific GeneratedDownload record
      pollSpecificDownloadStatus(libraryItemId, downloadInstanceId);
    }, 5000);
  }

  function stopPollingForLibraryItem(libraryItemId: number) {
    if (pollingIntervals[libraryItemId]) {
      clearInterval(pollingIntervals[libraryItemId]);
      delete pollingIntervals[libraryItemId];
    }
  }

  function clearAllPolling() {
    Object.keys(pollingIntervals).forEach((libItemIdStr) => {
      const libItemId = parseInt(libItemIdStr, 10);
      stopPollingForLibraryItem(libItemId);
    });
  }

  return {
    libraryItems,
    isLoading,
    error,
    activeDownloadRequests,
    activeDownloadErrors,
    isProcessingDownload,
    fetchLibraryItems,
    addItemToLibrary,
    removeItemFromLibrary,
    getLibraryItemByReleaseId,
    requestLibraryItemDownload,
    startPollingForLibraryItem,
    stopPollingForLibraryItem,
    clearAllPolling,
  };
});
