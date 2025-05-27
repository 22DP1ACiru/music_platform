<script setup lang="ts">
import { ref, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";
import ReleaseForm, {
  type ReleaseFormData as FormComponentState,
  type TrackFormData,
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
  download_file: string | null;
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
const trackSpecificErrors = ref<Record<string, string>>({});

const formatTrackError = (
  trackId: string | number,
  trackTitle: string | undefined,
  trackErrors: any
): string => {
  let messages: string[] = [];
  if (typeof trackErrors === "string") {
    messages.push(trackErrors);
  } else if (Array.isArray(trackErrors)) {
    messages = messages.concat(trackErrors.map((e) => String(e)));
  } else if (typeof trackErrors === "object" && trackErrors !== null) {
    for (const field in trackErrors) {
      const fieldErrors = trackErrors[field];
      if (Array.isArray(fieldErrors)) {
        messages.push(`${field}: ${fieldErrors.join(", ")}`);
      } else {
        messages.push(`${field}: ${String(fieldErrors)}`);
      }
    }
  }
  return `Track "${
    trackTitle || `ID: ${trackId}` || "Untitled"
  }": ${messages.join("; ")}`;
};

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
  trackSpecificErrors.value = {};

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
    !submittedFormData.cover_art_url
  ) {
    releaseUpdatePayload.append("cover_art", "");
  }

  submittedFormData.genre_names.forEach((name) =>
    releaseUpdatePayload.append("genre_names", name)
  );

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
      releaseUpdatePayload.append("currency", submittedFormData.currency);
    }
  } else {
    releaseUpdatePayload.append("minimum_price_nyp", "");
  }

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
        trackSpecificErrors.value[String(track.id)] = "Invalid track number.";
        continue;
      }

      if (track._isRemoved && track._originalId) {
        await axios.delete(`/tracks/${track._originalId}/`);
      } else if (!track._isRemoved) {
        const trackApiData = new FormData();
        trackApiData.append("title", track.title);
        trackApiData.append("track_number", trackNumberToSubmit.toString());
        if (track.audio_file_object) {
          trackApiData.append("audio_file", track.audio_file_object);
        }

        track.genre_names.forEach((name) =>
          trackApiData.append("genre_names", name)
        );

        try {
          if (track._isNew) {
            if (!track.title || !track.audio_file_object) {
              trackSpecificErrors.value[String(track.id)] =
                "New track missing title or audio file.";
              continue;
            }
            trackApiData.append("release", submittedFormData.id.toString());
            await axios.post("/tracks/", trackApiData);
          } else if (track._originalId) {
            const originalTrack = initialReleaseData.value?.tracks.find(
              (t) => t._originalId === track._originalId
            );
            let hasChanges = false;
            if (originalTrack) {
              if (originalTrack.title !== track.title) hasChanges = true;
              if (originalTrack.track_number !== track.track_number)
                hasChanges = true;
              if (track.audio_file_object) hasChanges = true;
              if (
                JSON.stringify((originalTrack.genre_names || []).sort()) !==
                JSON.stringify((track.genre_names || []).sort())
              )
                hasChanges = true;
            } else {
              hasChanges = true;
            }

            if (hasChanges) {
              await axios.patch(`/tracks/${track._originalId}/`, trackApiData, {
                headers: { "Content-Type": "multipart/form-data" },
              });
            }
          }
        } catch (trackError: any) {
          console.error(
            `EditReleaseView: Failed to update/create track "${track.title}":`,
            trackError
          );
          const trackErrorMessage = formatTrackError(
            track.id,
            track.title,
            trackError.response?.data
          );
          trackSpecificErrors.value[String(track.id)] = trackErrorMessage;
          if (!error.value)
            error.value =
              "One or more tracks failed to save. Please review track errors below.";
        }
      }
    }

    if (Object.keys(trackSpecificErrors.value).length > 0) {
      console.warn(
        "EditReleaseView: Some tracks failed to save. Release update might be partial."
      );
    } else {
      alert("Release updated successfully!");
      router.push({
        name: "release-detail",
        params: { id: submittedFormData.id },
      });
    }
  } catch (err: any) {
    console.error("EditReleaseView: Failed to update release:", err);
    if (axios.isAxiosError(err) && err.response) {
      const errors = err.response.data;
      let detailedError = "Failed to update release. ";
      if (typeof errors === "object" && errors !== null) {
        detailedError += Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${
                Array.isArray(messages) ? messages.join(", ") : String(messages)
              }`
          )
          .join(" | ");
      }
      error.value = `Release Update Error (${err.response.status}): ${detailedError}`;
      if (errors && errors.cover_art && Array.isArray(errors.cover_art)) {
        if (errors.cover_art.some((e: string) => e.includes("GIF"))) {
          error.value += " GIFs are not allowed for cover art.";
        }
      }
    } else {
      error.value = "An unexpected error occurred during release update.";
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
    <div
      v-if="Object.keys(trackSpecificErrors).length > 0"
      class="track-errors-summary"
    >
      <h4>Track Update Issues:</h4>
      <ul>
        <li
          v-for="(msg, trackIdKey) in trackSpecificErrors"
          :key="trackIdKey"
          class="error-message"
        >
          {{ msg }}
        </li>
      </ul>
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
  color: var(--vt-c-red-dark);
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

.track-errors-summary {
  margin-top: 1rem;
  padding: 1rem;
  border: 1px solid var(--vt-c-red-dark);
  border-radius: 4px;
  background-color: var(--vt-c-red-soft);
}
.track-errors-summary h4 {
  color: var(--vt-c-red-dark);
  margin-top: 0;
  margin-bottom: 0.5rem;
}
.track-errors-summary ul {
  list-style: none;
  padding-left: 0;
}
.track-errors-summary li.error-message {
  background-color: transparent;
  border: none;
  padding: 0.2rem 0;
  margin-bottom: 0.3rem;
}
</style>
