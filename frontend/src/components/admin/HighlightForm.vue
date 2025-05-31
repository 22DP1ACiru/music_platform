<script setup lang="ts">
import { ref, reactive, onMounted, watch, type PropType, computed } from "vue";
import axios from "axios";
import type { HighlightItem, ReleaseSummary } from "@/types";
import ReleaseSelectorModal from "./ReleaseSelectorModal.vue"; // Import the modal

interface PaginatedReleasesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ReleaseSummary[];
}

interface HighlightFormData {
  id?: number;
  release: number | null;
  title: string;
  subtitle: string;
  description: string;
  custom_carousel_image_file: File | null;
  custom_carousel_image_url: string | null;
  is_active: boolean;
  order: number;
  display_start_datetime_str: string;
  display_end_datetime_str: string | null;
}

const props = defineProps({
  initialData: {
    type: Object as PropType<Partial<HighlightItem>>,
    default: () => ({}),
  },
  isEditMode: {
    type: Boolean,
    default: false,
  },
  isLoadingSubmit: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit-highlight", "cancel-form"]);

// Function to get current local date and time in YYYY-MM-DDTHH:mm format
const getCurrentLocalDateTimeString = () => {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const adjustedNow = new Date(now.getTime() - offset * 60 * 1000);
  return adjustedNow.toISOString().slice(0, 16);
};

const formState = reactive<HighlightFormData>({
  id: undefined,
  release: null,
  title: "",
  subtitle: "",
  description: "",
  custom_carousel_image_file: null,
  custom_carousel_image_url: null,
  is_active: true,
  order: 0,
  display_start_datetime_str: getCurrentLocalDateTimeString(), // Default to current local time
  display_end_datetime_str: null,
});

const coverArtPreviewUrl = ref<string | null>(null);
const removeExistingCoverArt = ref(false);

const isReleaseSelectorVisible = ref(false);
const selectedReleaseDisplay = ref<string | null>(null); // To show chosen release info

const formatDateTimeForApi = (dateTimeLocalString: string | null) => {
  if (!dateTimeLocalString) return null;
  try {
    // Input is local, convert to UTC for API
    return new Date(dateTimeLocalString).toISOString();
  } catch (e) {
    return null;
  }
};

const formatDateTimeForInput = (isoString: string | null | undefined) => {
  if (!isoString) return "";
  try {
    const date = new Date(isoString); // ISO string is UTC
    // Convert UTC to local time for the input field
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const day = date.getDate().toString().padStart(2, "0");
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  } catch (e) {
    return "";
  }
};

// Fetch the full release details if only an ID is present (e.g., on edit mode load)
async function fetchSelectedReleaseDetails(releaseId: number | null) {
  if (releaseId) {
    try {
      const response = await axios.get<ReleaseSummary>(
        `/releases/${releaseId}/`
      );
      selectedReleaseDisplay.value = `${response.data.title} (by ${
        response.data.artist?.name || "Unknown Artist"
      })`;
    } catch (error) {
      console.error("Failed to fetch selected release details:", error);
      selectedReleaseDisplay.value = `Release ID: ${releaseId} (Details unavailable)`;
    }
  } else {
    selectedReleaseDisplay.value = null;
  }
}

watch(
  () => props.initialData,
  (newData) => {
    formState.id = newData?.id;
    formState.release = newData?.release || null;
    formState.title = newData?.title || "";
    formState.subtitle = newData?.subtitle || "";
    formState.description = newData?.description || "";
    formState.custom_carousel_image_url =
      newData?.custom_carousel_image || null;
    formState.is_active =
      newData?.is_active !== undefined ? newData.is_active : true;
    formState.order = newData?.order || 0;

    // Set start time: if editing and data has it, format it. Otherwise, default to current.
    formState.display_start_datetime_str =
      props.isEditMode && newData?.display_start_datetime
        ? formatDateTimeForInput(newData.display_start_datetime)
        : getCurrentLocalDateTimeString();

    formState.display_end_datetime_str = formatDateTimeForInput(
      newData?.display_end_datetime
    );

    coverArtPreviewUrl.value = newData?.custom_carousel_image || null;
    formState.custom_carousel_image_file = null;
    removeExistingCoverArt.value = false;

    if (formState.release) {
      fetchSelectedReleaseDetails(formState.release);
    } else {
      selectedReleaseDisplay.value = null;
    }
  },
  { immediate: true, deep: true }
);

const handleCoverArtChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    if (file.type === "image/gif") {
      alert("Animated GIFs are not allowed. Please use JPG, PNG, or WEBP.");
      target.value = "";
      formState.custom_carousel_image_file = null;
      if (
        coverArtPreviewUrl.value &&
        coverArtPreviewUrl.value.startsWith("blob:")
      ) {
        URL.revokeObjectURL(coverArtPreviewUrl.value);
      }
      coverArtPreviewUrl.value = formState.custom_carousel_image_url;
      return;
    }
    formState.custom_carousel_image_file = file;
    removeExistingCoverArt.value = false;
    if (
      coverArtPreviewUrl.value &&
      coverArtPreviewUrl.value.startsWith("blob:")
    ) {
      URL.revokeObjectURL(coverArtPreviewUrl.value);
    }
    coverArtPreviewUrl.value = URL.createObjectURL(file);
  } else {
    formState.custom_carousel_image_file = null;
    if (
      coverArtPreviewUrl.value &&
      coverArtPreviewUrl.value.startsWith("blob:")
    ) {
      URL.revokeObjectURL(coverArtPreviewUrl.value);
    }
    coverArtPreviewUrl.value = formState.custom_carousel_image_url;
  }
};

const triggerRemoveCoverArt = () => {
  removeExistingCoverArt.value = true;
  formState.custom_carousel_image_file = null;
  if (
    coverArtPreviewUrl.value &&
    coverArtPreviewUrl.value.startsWith("blob:")
  ) {
    URL.revokeObjectURL(coverArtPreviewUrl.value);
  }
  coverArtPreviewUrl.value = null;
};

const handleReleaseSelected = (selectedRelease: ReleaseSummary) => {
  formState.release = selectedRelease.id;
  selectedReleaseDisplay.value = `${selectedRelease.title} (by ${
    selectedRelease.artist?.name || "Unknown Artist"
  })`;
  isReleaseSelectorVisible.value = false;
};

const handleSubmit = () => {
  if (formState.release === null) {
    alert("Please select a release.");
    return;
  }

  const submissionPayload = new FormData();
  if (formState.id) {
    submissionPayload.append("id", formState.id.toString());
  }
  submissionPayload.append("release", formState.release.toString());
  submissionPayload.append("title", formState.title);
  submissionPayload.append("subtitle", formState.subtitle);
  submissionPayload.append("description", formState.description);
  submissionPayload.append("is_active", formState.is_active.toString());
  submissionPayload.append("order", formState.order.toString());

  const startDateTime = formatDateTimeForApi(
    formState.display_start_datetime_str
  );
  if (startDateTime) {
    submissionPayload.append("display_start_datetime", startDateTime);
  } else {
    alert("Invalid Start Date/Time");
    return;
  }

  const endDateTime = formatDateTimeForApi(formState.display_end_datetime_str);
  if (formState.display_end_datetime_str && !endDateTime) {
    alert("Invalid End Date/Time. If set, it must be a valid date and time.");
    return;
  }
  if (endDateTime) {
    submissionPayload.append("display_end_datetime", endDateTime);
  } else {
    submissionPayload.append("display_end_datetime", "");
  }

  if (formState.custom_carousel_image_file) {
    submissionPayload.append(
      "custom_carousel_image",
      formState.custom_carousel_image_file
    );
  } else if (removeExistingCoverArt.value) {
    submissionPayload.append("custom_carousel_image", "");
  }

  emit("submit-highlight", submissionPayload);
};
</script>

<template>
  <form @submit.prevent="handleSubmit" class="highlight-form">
    <div class="form-group">
      <label for="highlight-release-display">Release:</label>
      <div class="selected-release-display">
        {{ selectedReleaseDisplay || "No release selected" }}
      </div>
      <button
        type="button"
        @click="isReleaseSelectorVisible = true"
        class="select-release-btn"
      >
        {{ formState.release ? "Change Release" : "Select Release" }}
      </button>
    </div>

    <ReleaseSelectorModal
      :is-visible="isReleaseSelectorVisible"
      @close="isReleaseSelectorVisible = false"
      @release-selected="handleReleaseSelected"
    />

    <div class="form-group">
      <label for="highlight-title"
        >Highlight Title (Optional - max 70 chars):</label
      >
      <input
        type="text"
        id="highlight-title"
        v-model="formState.title"
        maxlength="70"
        placeholder="Defaults to Release Title"
      />
    </div>

    <div class="form-group">
      <label for="highlight-subtitle"
        >Subtitle (Optional - max 64 chars):</label
      >
      <input
        type="text"
        id="highlight-subtitle"
        v-model="formState.subtitle"
        maxlength="64"
      />
    </div>

    <div class="form-group">
      <label for="highlight-description"
        >Description (Optional - max 255 chars):</label
      >
      <textarea
        id="highlight-description"
        v-model="formState.description"
        rows="3"
        maxlength="255"
      ></textarea>
    </div>

    <div class="form-group">
      <label for="highlight-image"
        >Custom Carousel Image (Optional, JPG/PNG/WEBP):</label
      >
      <div class="cover-art-preview-container">
        <img
          v-if="coverArtPreviewUrl"
          :src="coverArtPreviewUrl"
          alt="Image Preview"
          class="cover-art-preview"
        />
        <div v-else class="cover-art-preview placeholder">No Custom Image</div>
      </div>
      <input
        type="file"
        id="highlight-image"
        @change="handleCoverArtChange"
        accept="image/jpeg,image/png,image/webp"
      />
      <button
        v-if="
          coverArtPreviewUrl &&
          (formState.custom_carousel_image_url ||
            formState.custom_carousel_image_file)
        "
        type="button"
        @click="triggerRemoveCoverArt"
        class="remove-cover-btn"
        :disabled="isLoadingSubmit"
      >
        Remove Custom Image
      </button>
      <p v-if="formState.custom_carousel_image_file" class="file-info">
        New: {{ formState.custom_carousel_image_file.name }}
      </p>
      <p
        v-if="removeExistingCoverArt && !formState.custom_carousel_image_file"
        class="file-info"
      >
        Custom image will be removed.
      </p>
    </div>

    <div class="form-group form-group-datetime">
      <div>
        <label for="highlight-start-datetime"
          >Display Start Date & Time (Local):</label
        >
        <input
          type="datetime-local"
          id="highlight-start-datetime"
          v-model="formState.display_start_datetime_str"
          required
        />
      </div>
      <div>
        <label for="highlight-end-datetime"
          >Display End Date & Time (Optional, Local):</label
        >
        <input
          type="datetime-local"
          id="highlight-end-datetime"
          v-model="formState.display_end_datetime_str"
        />
      </div>
    </div>

    <div class="form-group">
      <label for="highlight-order"
        >Order (e.g., 0 is first - must be unique):</label
      >
      <input
        type="number"
        id="highlight-order"
        v-model.number="formState.order"
        min="0"
      />
    </div>

    <div class="form-group form-group-checkbox">
      <input
        type="checkbox"
        id="highlight-active"
        v-model="formState.is_active"
      />
      <label for="highlight-active">Active (display on homepage)</label>
    </div>

    <div class="form-actions">
      <button type="submit" :disabled="isLoadingSubmit">
        {{
          isLoadingSubmit
            ? "Saving..."
            : isEditMode
            ? "Save Changes"
            : "Create Highlight"
        }}
      </button>
      <button
        type="button"
        @click="$emit('cancel-form')"
        :disabled="isLoadingSubmit"
        class="cancel-button"
      >
        Cancel
      </button>
    </div>
  </form>
</template>

<style scoped>
.highlight-form {
  background-color: var(--color-background);
  padding: 1.5rem;
  border-radius: 6px;
}
.form-group {
  margin-bottom: 1rem;
}
.form-group label {
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 500;
  color: var(--color-text);
}
.form-group input[type="text"],
.form-group input[type="number"],
.form-group input[type="file"],
.form-group input[type="datetime-local"],
/* .form-group select, Remove select styles */
.form-group textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  font-size: 1em;
}
.form-group-datetime {
  display: flex;
  gap: 1rem;
}
.form-group-datetime > div {
  flex: 1;
}

.selected-release-display {
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-mute);
  min-height: calc(0.6rem * 2 + 1.2em); /* Match input height */
  display: flex;
  align-items: center;
  margin-bottom: 0.5rem;
  font-style: italic;
  color: var(--color-text-light);
}

.select-release-btn {
  padding: 0.5rem 1rem;
  font-size: 0.9em;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}
.select-release-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.cover-art-preview-container {
  margin-bottom: 0.5rem;
}
.cover-art-preview {
  max-width: 250px;
  max-height: 150px;
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  display: block;
}
.cover-art-preview.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-background-mute);
  color: var(--color-text-light);
  font-style: italic;
  height: 150px;
}

.remove-cover-btn {
  font-size: 0.8em;
  padding: 0.2em 0.5em;
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  border-radius: 4px;
  margin-top: 0.3rem;
  cursor: pointer;
}
.remove-cover-btn:hover {
  border-color: var(--vt-c-red);
  color: var(--vt-c-red);
}
.file-info {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text-light);
  margin-top: 0.2rem;
}

.form-group-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.form-group-checkbox input[type="checkbox"] {
  width: auto;
  margin-right: 0.3em;
}
.form-group-checkbox label {
  margin-bottom: 0;
  font-weight: normal;
}

.form-actions {
  margin-top: 1.5rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}
.form-actions button {
  padding: 0.7rem 1.5rem;
  border-radius: 5px;
  cursor: pointer;
}
.form-actions button[type="submit"] {
  background-color: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
}
.form-actions button[type="submit"]:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}
.cancel-button {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
</style>
