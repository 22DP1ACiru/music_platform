<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import ReleaseForm, {
  type ReleaseFormData as FormComponentState,
  type TrackFormData as FormTrackData,
} from "@/components/ReleaseForm.vue"; // Import the new component and types

const authStore = useAuthStore();
const router = useRouter();

const isLoading = ref(false);
const error = ref<string | null>(null);

const handleFormSubmit = async (submittedFormData: FormComponentState) => {
  isLoading.value = true;
  error.value = null;

  if (!authStore.hasArtistProfile) {
    error.value =
      "Artist profile could not be confirmed. Cannot create release.";
    isLoading.value = false;
    return;
  }
  // The form component now provides fullReleaseDateTimeForSubmission as release_date_for_api
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

  try {
    const releaseResponse = await axios.post("/releases/", releaseApiData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    const newReleaseId = releaseResponse.data.id;

    for (const track of submittedFormData.tracks) {
      if (track._isRemoved) continue; // Should not happen for new tracks in create mode

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
        continue;
      }
      const trackApiData = new FormData();
      trackApiData.append("title", track.title);
      trackApiData.append("audio_file", track.audio_file_object); // Use audio_file_object
      trackApiData.append("release", newReleaseId.toString());
      trackApiData.append("track_number", track.track_number.toString());
      track.genre_names.forEach((genre) => {
        trackApiData.append("genre_names", genre);
      });
      await axios.post("/tracks/", trackApiData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    }
    alert("Release created successfully!");
    router.push({ name: "release-detail", params: { id: newReleaseId } });
  } catch (err: any) {
    console.error(
      "CreateReleaseView: Failed to create release or tracks:",
      err
    );
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
        detailedError || "Failed to create release."
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
      error.value = "An unexpected error occurred.";
    }
  } finally {
    isLoading.value = false;
  }
};

const handleCancel = () => {
  router.push({ name: "releases" }); // Navigate to releases list on cancel
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
.error-message {
  color: var(--vt-c-red);
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
</style>
