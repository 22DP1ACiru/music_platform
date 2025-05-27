<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import ReleaseForm, {
  type ReleaseFormData as FormComponentState,
  type TrackFormData,
} from "@/components/ReleaseForm.vue";

const authStore = useAuthStore();
const router = useRouter();

const isLoading = ref(false);
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

const handleFormSubmit = async (submittedFormData: FormComponentState) => {
  isLoading.value = true;
  error.value = null;
  trackSpecificErrors.value = {};

  if (!authStore.hasArtistProfile) {
    error.value =
      "Artist profile could not be confirmed. Cannot create release.";
    isLoading.value = false;
    return;
  }

  const releaseDateForApi = (submittedFormData as any).release_date_for_api;
  if (!releaseDateForApi) {
    error.value = "Invalid release date or time specified by form component.";
    isLoading.value = false;
    return;
  }

  const releaseApiData = new FormData();
  releaseApiData.append("title", submittedFormData.title);
  releaseApiData.append("release_type", submittedFormData.release_type);
  releaseApiData.append("release_date", releaseDateForApi);
  releaseApiData.append(
    "is_published",
    submittedFormData.is_published.toString()
  );

  if (submittedFormData.new_cover_art_file) {
    releaseApiData.append("cover_art", submittedFormData.new_cover_art_file);
  }
  submittedFormData.genre_names.forEach((genre) => {
    releaseApiData.append("genre_names", genre);
  });

  releaseApiData.append("pricing_model", submittedFormData.pricing_model);
  if (submittedFormData.pricing_model === "PAID") {
    if (
      submittedFormData.price !== null &&
      submittedFormData.price !== undefined
    ) {
      releaseApiData.append("price", submittedFormData.price.toString());
    }
    if (submittedFormData.currency) {
      releaseApiData.append("currency", submittedFormData.currency);
    }
  }
  if (submittedFormData.pricing_model === "NYP") {
    if (
      submittedFormData.minimum_price_nyp !== null &&
      submittedFormData.minimum_price_nyp !== undefined
    ) {
      releaseApiData.append(
        "minimum_price_nyp",
        submittedFormData.minimum_price_nyp.toString()
      );
    }
    if (submittedFormData.currency) {
      releaseApiData.append("currency", submittedFormData.currency);
    }
  }

  let newReleaseId: number | null = null;
  try {
    const releaseResponse = await axios.post("/releases/", releaseApiData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    newReleaseId = releaseResponse.data.id;

    for (const track of submittedFormData.tracks) {
      if (track._isRemoved) continue;

      if (
        !track.title ||
        !track.audio_file_object ||
        track.track_number === null
      ) {
        console.warn(
          `Skipping track ${
            track.title || "Untitled"
          } due to missing title, file, or track number.`
        );
        trackSpecificErrors.value[String(track.id)] =
          "Missing title, file, or track number.";
        continue;
      }
      const trackApiData = new FormData();
      trackApiData.append("title", track.title);
      trackApiData.append("audio_file", track.audio_file_object);
      trackApiData.append("release", newReleaseId.toString());
      trackApiData.append("track_number", track.track_number.toString());
      track.genre_names.forEach((genre) => {
        trackApiData.append("genre_names", genre);
      });

      try {
        await axios.post("/tracks/", trackApiData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } catch (trackError: any) {
        console.error(
          `CreateReleaseView: Failed to create track "${track.title}":`,
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
            "One or more tracks failed to upload. Please review track errors below.";
      }
    }

    if (Object.keys(trackSpecificErrors.value).length > 0) {
      console.warn(
        "CreateReleaseView: Some tracks failed to save. Release might be partial."
      );
    } else {
      alert("Release created successfully!");
      router.push({ name: "release-detail", params: { id: newReleaseId } });
    }
  } catch (err: any) {
    console.error(
      "CreateReleaseView: Failed to create release:", // Main error now focuses on release part
      err
    );
    if (axios.isAxiosError(err) && err.response) {
      const errors = err.response.data;
      let detailedError = "Failed to create release. ";
      if (typeof errors === "object" && errors !== null) {
        detailedError += Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${
                Array.isArray(messages) ? messages.join(", ") : messages
              }`
          )
          .join(" | ");
      }
      error.value = `Release Error (${err.response.status}): ${detailedError}`;
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
      error.value = "An unexpected error occurred while creating the release.";
    }
  } finally {
    isLoading.value = false;
  }
};

const handleCancel = () => {
  router.push({ name: "releases" });
};
</script>

<template>
  <div class="create-release-page view-container">
    <h2>Upload New Release</h2>
    <div v-if="!authStore.hasArtistProfile && !isLoading" class="error-message">
      You must have an artist profile to create a release. Please
      <RouterLink :to="{ name: 'profile' }">visit your profile</RouterLink> to
      create one.
    </div>

    <ReleaseForm
      v-else
      :is-edit-mode="false"
      :is-loading-submit="isLoading"
      @submit-release="handleFormSubmit"
      @cancel-form="handleCancel"
    />

    <div v-if="error" class="error-message backend-error">{{ error }}</div>
    <div
      v-if="Object.keys(trackSpecificErrors).length > 0"
      class="track-errors-summary"
    >
      <h4>Track Upload Issues:</h4>
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
.error-message {
  color: var(--vt-c-red-dark);
  margin-bottom: 1rem;
  padding: 0.7rem;
  border: 1px solid var(--vt-c-red-dark);
  border-radius: 4px;
  background-color: var(--vt-c-red-soft);
  text-align: left;
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
