<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";
import ReleaseForm, {
  type ReleaseFormData as FormComponentState,
  type TrackFormData as FormTrackData,
} from "@/components/ReleaseForm.vue";

// Interface for API response when fetching existing release
interface ApiReleaseTrack {
  id: number;
  title: string;
  track_number: number | null;
  audio_file: string; // URL
  genres_data?: { id: number; name: string }[];
}
interface ApiReleaseData {
  id: number;
  title: string;
  release_type: "ALBUM" | "EP" | "SINGLE";
  release_date: string; // ISO string
  cover_art: string | null;
  genres_data: { id: number; name: string }[];
  is_published: boolean;
  tracks: ApiReleaseTrack[];
}

const router = useRouter();
const route = useRoute();

const initialReleaseData = ref<FormComponentState | null>(null);
const isLoadingData = ref(true); // For fetching initial data
const isSubmittingForm = ref(false); // For form submission loading state
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
      new_cover_art_file: undefined, // No new file initially
      genre_names: apiData.genres_data.map((g) => g.name),
      is_published: apiData.is_published,
      tracks: apiData.tracks.map((apiTrack) => ({
        id: apiTrack.id, // DB ID
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
  }
  // To clear cover art, backend must support empty string or specific flag.
  // If new_cover_art_file is undefined AND cover_art_url is null (after user interaction), it implies removal.
  else if (
    !submittedFormData.new_cover_art_file &&
    !submittedFormData.cover_art_url
  ) {
    releaseUpdatePayload.append("cover_art", ""); // Signal to clear
  }

  submittedFormData.genre_names.forEach((name) =>
    releaseUpdatePayload.append("genre_names", name)
  );

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
          if (!track.title || !track.audio_file_object) continue;
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
            updateTrackPayload.append("audio_file", track.audio_file_object);
          }
          track.genre_names.forEach((name) =>
            updateTrackPayload.append("genre_names", name)
          );
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
  /* Common styling for view pages */
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
