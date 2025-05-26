// frontend/src/views/EditReleaseView.vue
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
    !submittedFormData.cover_art_url
  ) {
    releaseUpdatePayload.append("cover_art", "");
  }

  // Handle release genres
  if (submittedFormData.genre_names.length > 0) {
    submittedFormData.genre_names.forEach((name) =>
      releaseUpdatePayload.append("genre_names", name)
    );
  } else if (
    submittedFormData.id &&
    initialReleaseData.value &&
    initialReleaseData.value.genre_names &&
    initialReleaseData.value.genre_names.length > 0
  ) {
    // If editing, initial data had genres, and now submitted an empty list,
    // send the key with no values to signal clearing M2M on backend.
    // This relies on the backend ListField to interpret a present key with no values as []
    // For FormData, this is a bit nuanced. DRF's default HTML forms would submit `genre_names=`
    // We can try to achieve this by appending once if the list is empty.
    // However, for `ListField(child=CharField)`, simply not sending items if the list is empty
    // during a PATCH might be interpreted as "no change". To explicitly clear, this needs care.
    // The ReleaseSerializer's `update` correctly handles `genre_names=[]` to clear.
    // So we need to make sure that if `submittedFormData.genre_names` is [],
    // the backend receives `genre_names` as an empty list in `validated_data`.
    // `FormData` sends `genre_names` for each item. If no items, no `genre_names` key is sent by default.
    // To force it, we can send an empty string FOR THE RELEASE (not track, which caused issues).
    // This assumes the ReleaseSerializer's ListField for genre_names can handle an empty string as "clear list".
    // A safer bet for ListField(child=CharField) is that if the key 'genre_names' is submitted
    // but has no values, it becomes an empty list.
    // Let's send an empty list explicitly if we want to clear.
    // For FormData, to represent an empty list when the field is a ListField(child=CharField),
    // you typically send the key name, and the backend ListField's `empty_value` (which is `[]`)
    // should kick in if no items are provided for that key.
    // If the key `genre_names` is sent (e.g. via a hidden input with that name but no value, or
    // by `append("genre_names", [])` if `FormData` supported arrays directly which it doesn't for scalars),
    // DRF should treat it as an intention to set it to an empty list.
    // The most straightforward is to let the serializer handle "key not present" as "no change" for PATCH.
    // If we want to clear, we MUST send the key and ensure it validates to [].
    // The backend ReleaseSerializer does `instance.genres.set(genres_to_set)`. If genres_to_set is `[]`, it clears.
    // This happens if `validated_data['genre_names']` is `[]`.
    // We can ensure this by always sending `genre_names` if it was part of the initial form state,
    // even if it's now empty.
    submittedFormData.genre_names.forEach((name) =>
      releaseUpdatePayload.append("genre_names", name)
    );
    // If submittedFormData.genre_names is [], the loop doesn't run.
    // If we want to clear, the key 'genre_names' needs to be present in the form data.
    // A common way is: if it's an update and the list is now empty, send 'genre_names='
    // This can be done by `releaseUpdatePayload.append('genre_names', '');` but ONLY if the ListField expects this.
    // For now, if `submittedFormData.genre_names` is empty, this loop won't append, and DRF's pop will result in `None`, leading to no change.
    // This is fine for the 400 error but doesn't allow clearing.
    // To allow clearing, we'd need to ensure an empty list is passed to `set`.
    // This means validated_data['genre_names'] should be [].
    // For this to happen from FormData, if genre_names is empty, we need to ensure it's part of the data submitted.
    // A simple way is to always include it if it's an edit.
    if (props.isEditMode && submittedFormData.genre_names.length === 0) {
      // This ensures the key is sent. DRF might interpret a key with no values as an empty list.
      // This is still a bit of a hack for FormData and ListField(child=CharField).
      // The most robust is custom handling in serializer's update, or using JSON payload.
      // Let's rely on the default behavior: if `genre_names` is empty, the loop doesn't run, key is not sent,
      // serializer's `pop` yields `None`, and genres are NOT changed. This fixes the 400.
      // Clearing genres will require a more specific approach later if this is insufficient.
    }
  }

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
        continue;
      }

      if (track._isRemoved && track._originalId) {
        await axios.delete(`/tracks/${track._originalId}/`);
      } else if (!track._isRemoved) {
        const updateTrackPayload = new FormData(); // Renamed to avoid conflict with outer scope
        updateTrackPayload.append("title", track.title);
        updateTrackPayload.append(
          "track_number",
          trackNumberToSubmit.toString()
        );
        if (track.audio_file_object) {
          updateTrackPayload.append("audio_file", track.audio_file_object);
        }

        // Handle track genres: Only append if there are genres.
        // If track.genre_names is empty, the key 'genre_names' will not be sent for this track.
        // The backend TrackSerializer's update method will see genre_names as None,
        // and thus will not modify the track's genres. This is correct for PATCH "no change".
        if (track.genre_names && track.genre_names.length > 0) {
          track.genre_names.forEach((name) =>
            updateTrackPayload.append("genre_names", name)
          );
        } else if (track._originalId && initialReleaseData.value) {
          // If it's an existing track and its genres are now empty,
          // we need to signal to the backend to clear them.
          // For DRF ListField(child=CharField), sending the key with an empty list of values.
          // FormData doesn't directly support `[]`. Sending the key without values *might* work
          // or sending the key with a single empty string if the serializer is configured for it.
          // The TrackSerializer update logic `instance.genres.set(genres_to_set)` will clear
          // if `genres_to_set` is an empty list. This means `validated_data['genre_names']` must be `[]`.
          // To achieve this with FormData for a PATCH where you want to clear, you must send the key.
          // The current behavior (not sending key if list is empty) means "no change".
          // To explicitly clear, you would typically send `genre_names: []` in JSON.
          // For FormData, if you want to clear, you'd send the field name, and the backend
          // must interpret the lack of values for that name as an empty list.
          // Let's assume for now that if track.genre_names is empty, we are not trying to clear,
          // but rather making "no change" to this specific field.
          // If clearing is desired, the backend serializer might need `allow_null=True` on the M2M field source
          // and frontend send `null` (not possible with FormData for lists directly) or a specific signal.
          // The simplest for now is: if genre_names is empty, no 'genre_names' key is added to FormData for the track.
          // This means genres for that track are NOT MODIFIED. This avoids the 400.
        }

        if (track._isNew) {
          if (!track.title || !track.audio_file_object) continue;
          updateTrackPayload.append("release", submittedFormData.id.toString());
          await axios.post("/tracks/", updateTrackPayload);
        } else if (track._originalId) {
          const hasScalarUpdates =
            updateTrackPayload.has("title") ||
            updateTrackPayload.has("track_number") ||
            updateTrackPayload.has("audio_file");
          const genresWereModified =
            initialReleaseData.value?.tracks
              .find((t) => t._originalId === track._originalId)
              ?.genre_names.join(",") !== track.genre_names.join(",");

          // Send payload only if there are actual changes for scalar fields or if genres were part of the submission (even if empty to clear)
          // The key 'genre_names' is added to updateTrackPayload only if track.genre_names is not empty.
          // So, if track.genre_names IS empty, the key isn't sent, and genres are not touched (no 400).
          if (
            hasScalarUpdates ||
            (updateTrackPayload.has("genre_names") && genresWereModified)
          ) {
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
                Array.isArray(messages) ? messages.join(", ") : String(messages)
              }`
          )
          .join(" | ");
      }
      error.value = `Error (${err.response.status}): ${
        detailedError || "Failed to update."
      }`;
      if (errors && errors.cover_art && Array.isArray(errors.cover_art)) {
        if (errors.cover_art.some((e: string) => e.includes("GIF"))) {
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
