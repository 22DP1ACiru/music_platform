import { defineStore } from "pinia";
import { ref, computed, onUnmounted } from "vue"; // Added onUnmounted for store cleanup
import axios from "axios";
import type { ReleaseDetail, GeneratedDownloadStatus } from "@/types";

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

  const pollingIntervals: Record<number, number | undefined> = {};

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
    acquisitionType: "FREE" | "PURCHASED" | "NYP" // Corrected from "PAID" to "PURCHASED" to align with your type
  ) {
    if (getLibraryItemByReleaseId.value(releaseId)) {
      console.log("Library Store: Item already in library.");
      // Consider updating acquisition_type if it's different and more favorable (e.g. FREE -> PURCHASED)
      const existingItem = getLibraryItemByReleaseId.value(releaseId);
      if (existingItem && existingItem.acquisition_type !== acquisitionType) {
        // This is a more complex scenario: what if it was FREE and now it's PURCHASED?
        // For now, if it exists, we assume it's fine. The backend `get_or_create` in `add_item_to_library`
        // might also need refinement if types can change.
        // For simplicity, just return true if it exists.
      }
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
      // Clean up state related to this removed item
      stopPollingForLibraryItem(libraryItemId); // Ensure polling stops
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
        startPollingForLibraryItem(libraryItemId, response.data.id);
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

  async function pollSpecificDownloadStatus(
    libraryItemId: number,
    downloadInstanceId: number
  ) {
    // No need to set isProcessingDownload here, it's for the initial request.
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
          "Download request not found during polling. It might have been cleaned up or an error occurred.";
        // Update the status to reflect it's no longer actively processing/pending for this UI instance
        if (activeDownloadRequests.value[libraryItemId]) {
          activeDownloadRequests.value[libraryItemId]!.status = "FAILED"; // Or a new 'UNKNOWN' status
          activeDownloadRequests.value[libraryItemId]!.failure_reason =
            "Polling could not find the download record.";
        }
      } else {
        activeDownloadErrors.value[libraryItemId] =
          "Error checking download status during polling.";
      }
      stopPollingForLibraryItem(libraryItemId);
    }
  }

  function startPollingForLibraryItem(
    libraryItemId: number,
    downloadInstanceId: number
  ) {
    stopPollingForLibraryItem(libraryItemId); // Clear existing interval for this item first
    console.log(
      `Library Store: Started polling for library item ${libraryItemId}, download instance ${downloadInstanceId}`
    );
    pollSpecificDownloadStatus(libraryItemId, downloadInstanceId); // Initial poll
    pollingIntervals[libraryItemId] = window.setInterval(() => {
      pollSpecificDownloadStatus(libraryItemId, downloadInstanceId);
    }, 5000); // Poll every 5 seconds
  }

  function stopPollingForLibraryItem(libraryItemId: number) {
    if (pollingIntervals[libraryItemId]) {
      console.log(
        `Library Store: Stopped polling for library item ${libraryItemId}`
      );
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

  // --- Page Visibility API Handler ---
  const handleVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      console.log(
        "Library Store: Tab became visible. Re-checking active downloads."
      );
      for (const itemIdStr in activeDownloadRequests.value) {
        const itemId = parseInt(itemIdStr);
        const request = activeDownloadRequests.value[itemId];
        if (
          request &&
          (request.status === "PENDING" || request.status === "PROCESSING")
        ) {
          console.log(
            `Library Store: Forcing poll for visible tab on item ${itemId}, download ${request.id}`
          );
          pollSpecificDownloadStatus(itemId, request.id); // request.id is GeneratedDownload.id
        }
      }
    }
  };

  // Setup visibility listener when the store is initialized
  // This assumes the store is initialized once per application lifecycle.
  if (typeof document !== "undefined") {
    // Ensure document exists (for SSR/testing safety)
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }

  // Cleanup listener if the store instance were to be "unmounted" or disposed.
  // Pinia stores are generally global singletons, so this is more for completeness
  // or if you had a pattern of dynamically creating/destroying stores.
  onUnmounted(() => {
    if (typeof document !== "undefined") {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    }
    clearAllPolling(); // Also clear intervals when store/app might be closing down
  });

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
    startPollingForLibraryItem, // Export if direct control needed, though visibilityChange handles most cases
    stopPollingForLibraryItem, // Export for manual stop if necessary
    clearAllPolling,
  };
});
