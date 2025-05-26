<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";
import ReleaseForm, {
  type ReleaseFormData as FormComponentState,
} from "@/components/ReleaseForm.vue";

interface ApiReleaseTrack {
  id: number;
  title: string;
  track_number: number | null;
  audio_file: string;
  genres_data?: { id: number; name: string }[];
}
interface ApiReleaseData {
  id: number;
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date: string;
  cover_art: string | null;
  genres_data: { id: number; name: string }[];
  is_published: boolean;
  tracks: ApiReleaseTrack[];
  // Shop fields from backend
  download_file: string | null; // Musician-uploaded (legacy)
  pricing_model: "FREE" | "PAID" | "NYP";
  price: string | null;
  currency: string | null;
  minimum_price_nyp: string | null;
}

const router = useRouter();
const route = useRoute();

const initialReleaseData = ref<FormComponentState | null>(null);
const isLoadingData = ref(true);
const isSubmittingForm = ref(false);
const error = ref<string | null>(null);

const fetchReleaseForEdit = async (releaseId: string) => {
  isLoadingData.value = true;
  error.value = null;
  try {
    const response = await axios.get<ApiReleaseData>(`/releases/${releaseId}/`);
    const apiData = response.data;

    const releaseDateObj = new Date(apiData.release_date);

    initialReleaseData.value = {
      id: apiData.id,
      title: apiData.title,
      release_type: apiData.release_type,
      release_date_str: releaseDateObj.toISOString().split("T")[0],
      release_time_str: `${releaseDateObj
        .getHours()
        .toString()
        .padStart(2, "0")}:${releaseDateObj
        .getMinutes()
        .toString()
        .padStart(2, "0")}`,
      cover_art_url: apiData.cover_art,
      new_cover_art_file: undefined,
      genre_names: apiData.genres_data.map((g) => g.name),
      is_published: apiData.is_published,
      tracks: apiData.tracks.map((apiTrack) => ({
        id: apiTrack.id,
        _originalId: apiTrack.id,
        title: apiTrack.title,
        track_number: apiTrack.track_number,
        audio_file_url: apiTrack.audio_file,
        audio_file_object: undefined,
        genre_names: apiTrack.genres_data
          ? apiTrack.genres_data.map((g) => g.name)
          : [],
        _isNew: false,
        _isRemoved: false,
      })),
      pricing_model: apiData.pricing_model,
      price: apiData.price !== null ? parseFloat(apiData.price) : null,
      currency: apiData.currency,
      minimum_price_nyp:
        apiData.minimum_price_nyp !== null
          ? parseFloat(apiData.minimum_price_nyp)
          : null,
      // Note: We don't set download_file_url or new_download_file_object here
      // as that field is deprecated from the musician's form.
    };
  } catch (err: any) {
    console.error("EditReleaseView: Failed to fetch release data:", err);
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Release not found.";
    } else if (axios.isAxiosError(err) && err.response?.status === 403) {
      error.value = "You are not authorized to edit this release.";
    } else {
      error.value = "Could not load release details for editing.";
    }
  } finally {
    isLoadingData.value = false;
  }
};

const handleFormSubmit = async (submittedFormData: FormComponentState) => {
  if (!submittedFormData.id) {
    error.value = "Cannot update: Release ID is missing in form data.";
    return;
  }
  isSubmittingForm.value = true;
  error.value = null;

  const releaseDateForApi = (submittedFormData as any).release_date_for_api;
  if (!releaseDateForApi) {
    error.value = "Invalid release date or time from form component.";
    isSubmittingForm.value = false;
    return;
  }

  const releaseUpdatePayload = new FormData();
  releaseUpdatePayload.append("title", submittedFormData.title);
  releaseUpdatePayload.append("release_type", submittedFormData.release_type);
  releaseUpdatePayload.append("release_date", releaseDateForApi);
  releaseUpdatePayload.append(
    "is_published",
    submittedFormData.is_published.toString()
  );
  if (submittedFormData.new_cover_art_file) {
    releaseUpdatePayload.append(
      "cover_art",
      submittedFormData.new_cover_art_file
    );
  } else if (
    !submittedFormData.new_cover_art_file &&
    !submittedFormData.cover_art_url // If new is not set AND existing URL is cleared
  ) {
    releaseUpdatePayload.append("cover_art", ""); // Signal to clear
  }

  submittedFormData.genre_names.forEach((name) =>
    releaseUpdatePayload.append("genre_names", name)
  );

  // Pricing model fields
  releaseUpdatePayload.append("pricing_model", submittedFormData.pricing_model);
  if (submittedFormData.pricing_model === "PAID") {
    if (
      submittedFormData.price !== null &&
      submittedFormData.price !== undefined
    ) {
      releaseUpdatePayload.append("price", submittedFormData.price.toString());
    }
    if (submittedFormData.currency) {
      releaseUpdatePayload.append("currency", submittedFormData.currency);
    }
  } else {
    releaseUpdatePayload.append("price", "");
  }

  if (submittedFormData.pricing_model === "NYP") {
    if (
      submittedFormData.minimum_price_nyp !== null &&
      submittedFormData.minimum_price_nyp !== undefined
    ) {
      releaseUpdatePayload.append(
        "minimum_price_nyp",
        submittedFormData.minimum_price_nyp.toString()
      );
    }
    if (submittedFormData.currency) {
      // NYP also uses currency
      releaseUpdatePayload.append("currency", submittedFormData.currency);
    }
  } else {
    releaseUpdatePayload.append("minimum_price_nyp", "");
  }
  // NOTE: The musician-uploaded 'download_file' is no longer sent from this form.
  // If the backend requires it for PATCH and it's not nullable,
  // this might need adjustment on the backend or to send an empty string if allowed.
  // For now, assuming backend handles its absence gracefully for PATCH.

  try {
    await axios.patch(
      `/releases/${submittedFormData.id}/`,
      releaseUpdatePayload,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    for (const track of submittedFormData.tracks) {
      const trackNumberToSubmit = track.track_number;
      if (trackNumberToSubmit === null || trackNumberToSubmit <= 0) {
        console.warn(
          `Skipping track update for ${
            track.title || "Untitled"
          } due to invalid track number.`
        );
        continue;
      }

      if (track._isRemoved && track._originalId) {
        await axios.delete(`/tracks/${track._originalId}/`);
      } else if (!track._isRemoved) {
        if (track._isNew) {
          if (!track.title || !track.audio_file_object) continue; // New tracks must have audio
          const newTrackPayload = new FormData();
          newTrackPayload.append("title", track.title);
          newTrackPayload.append("audio_file", track.audio_file_object);
          newTrackPayload.append("release", submittedFormData.id.toString());
          newTrackPayload.append(
            "track_number",
            trackNumberToSubmit.toString()
          );
          track.genre_names.forEach((name) =>
            newTrackPayload.append("genre_names", name)
          );
          await axios.post("/tracks/", newTrackPayload);
        } else if (track._originalId) {
          const updateTrackPayload = new FormData();
          updateTrackPayload.append("title", track.title);
          updateTrackPayload.append(
            "track_number",
            trackNumberToSubmit.toString()
          );
          if (track.audio_file_object) {
            // Only send audio if it's a new file
            updateTrackPayload.append("audio_file", track.audio_file_object);
          }
          // Handle genres: if genre_names is empty, send it as such to clear them
          // If genre_names has items, send them.
          // If backend expects 'genre_names' key even if empty to clear, send empty array.
          // If backend clears if key is absent, can conditionally add.
          // For DRF, sending an empty list for a M2M usually clears it.
          track.genre_names.forEach((name) =>
            updateTrackPayload.append("genre_names", name)
          );
          // If track.genre_names is empty and you want to ensure genres are cleared:
          if (track.genre_names.length === 0) {
            // Depending on backend, you might need to send `genre_names: []`
            // For FormData, if you want to signal an empty list for clearing,
            // you might need a specific backend handling or send a special value.
            // Often, not sending the key implies "no change" for M2M on PATCH.
            // To clear, you often send an empty list in JSON, or handle lack of key as "clear".
            // For now, if genre_names is empty, the loop doesn't add, backend might not clear.
            // This line ensures an empty list is signaled if genres are empty
            if (!updateTrackPayload.has("genre_names")) {
              updateTrackPayload.append("genre_names", ""); // Or handle on backend to clear if key sent empty
            }
          }

          await axios.patch(
            `/tracks/${track._originalId}/`,
            updateTrackPayload,
            {
              headers: { "Content-Type": "multipart/form-data" },
            }
          );
        }
      }
    }
    alert("Release updated successfully!");
    router.push({
      name: "release-detail",
      params: { id: submittedFormData.id },
    });
  } catch (err: any) {
    console.error("EditReleaseView: Failed to update release or tracks:", err);
    if (axios.isAxiosError(err) && err.response) {
      const errors = err.response.data;
      let detailedError = "";
      if (typeof errors === "object" && errors !== null) {
        detailedError = Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${
                Array.isArray(messages) ? messages.join(", ") : messages
              }`
          )
          .join(" | ");
      }
      error.value = `Error (${err.response.status}): ${
        detailedError || "Failed to update."
      }`;
      if (
        err.response.data.cover_art &&
        Array.isArray(err.response.data.cover_art)
      ) {
        if (
          err.response.data.cover_art.some((e: string) => e.includes("GIF"))
        ) {
          error.value += " GIFs are not allowed for cover art.";
        }
      }
    } else {
      error.value = "An unexpected error occurred during update.";
    }
  } finally {
    isSubmittingForm.value = false;
  }
};

const handleCancel = () => {
  if (initialReleaseData.value?.id) {
    router.push({
      name: "release-detail",
      params: { id: initialReleaseData.value.id },
    });
  } else {
    router.push({ name: "releases" });
  }
};

onMounted(() => {
  const releaseId = route.params.id as string;
  if (releaseId) {
    fetchReleaseForEdit(releaseId);
  } else {
    error.value = "No release ID provided for editing.";
    isLoadingData.value = false;
  }
});

watch(
  () => route.params.id,
  (newId) => {
    if (newId && newId !== initialReleaseData.value?.id?.toString()) {
      fetchReleaseForEdit(newId as string);
    }
  }
);
</script>

<template>
  <div class="edit-release-page view-container">
    <h2>Edit Release</h2>
    <div v-if="isLoadingData" class="loading-message">
      Loading release data...
    </div>
    <div
      v-else-if="error && !initialReleaseData"
      class="error-message initial-load-error"
    >
      {{ error }}
    </div>

    <ReleaseForm
      v-if="initialReleaseData && !isLoadingData"
      :initial-data="initialReleaseData"
      :is-edit-mode="true"
      :is-loading-submit="isSubmittingForm"
      @submit-release="handleFormSubmit"
      @cancel-form="handleCancel"
    />

    <div v-if="error && initialReleaseData" class="error-message backend-error">
      {{ error }}
    </div>
  </div>
</template>

<style scoped>
.view-container {
  max-width: 850px;
  margin: 2rem auto;
  padding: 1.5rem 2rem;
  background-color: var(--color-background-soft);
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}
.view-container h2 {
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  text-align: center;
}
.loading-message {
  padding: 2rem;
  text-align: center;
  font-style: italic;
}
.error-message {
  color: var(--vt-c-red);
  margin-bottom: 1rem;
  padding: 0.7rem;
  border: 1px solid var(--vt-c-red-dark);
  border-radius: 4px;
  background-color: var(--vt-c-red-soft);
  text-align: left;
}
.initial-load-error {
  margin-top: 1rem;
}
.backend-error {
  margin-top: 1rem;
}
</style>
