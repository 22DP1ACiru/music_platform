<script setup lang="ts">
import { ref, watch, type PropType, onUnmounted } from "vue"; // Added onUnmounted
import axios from "axios";

// Interface for the data needed by the form
interface ArtistFormData {
  name: string;
  bio: string | null;
  location: string | null;
  website_url: string | null;
  artist_picture?: string | null; // Current URL for display
}

// Props: initial data and the artist's ID for the API endpoint
const props = defineProps({
  initialData: {
    type: Object as PropType<ArtistFormData>,
    required: true,
  },
  artistId: {
    type: String, // Artist ID is a number from backend, but route params are strings
    required: true,
  },
});

const emit = defineEmits(["artistUpdated", "cancelEdit", "updateError"]);

// Local state for form fields
const formData = ref<Partial<ArtistFormData>>({ ...props.initialData });
const artistPictureFile = ref<File | null>(null);
const artistPicturePreviewUrl = ref<string | null>(
  props.initialData.artist_picture || null
); // For preview
const removePicture = ref(false); // Flag to signal picture removal
const isLoading = ref(false);

// Reset form if initial data changes
watch(
  () => props.initialData,
  (newData) => {
    formData.value = { ...newData };
    artistPictureFile.value = null;
    if (
      artistPicturePreviewUrl.value &&
      artistPicturePreviewUrl.value.startsWith("blob:")
    ) {
      URL.revokeObjectURL(artistPicturePreviewUrl.value);
    }
    artistPicturePreviewUrl.value = newData.artist_picture || null;
    removePicture.value = false;
  },
  { deep: true }
);

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    const file = target.files[0];
    // GIF Validation (client-side)
    if (file.type === "image/gif") {
      alert("Animated GIFs are not allowed. Please use a JPG, PNG, or WEBP.");
      target.value = ""; // Clear the input
      artistPictureFile.value = null;
      if (
        artistPicturePreviewUrl.value &&
        artistPicturePreviewUrl.value.startsWith("blob:")
      ) {
        URL.revokeObjectURL(artistPicturePreviewUrl.value);
      }
      artistPicturePreviewUrl.value = props.initialData.artist_picture || null;
      return;
    }

    artistPictureFile.value = file;
    removePicture.value = false;

    if (
      artistPicturePreviewUrl.value &&
      artistPicturePreviewUrl.value.startsWith("blob:")
    ) {
      URL.revokeObjectURL(artistPicturePreviewUrl.value);
    }
    artistPicturePreviewUrl.value = URL.createObjectURL(file);
  } else {
    artistPictureFile.value = null;
    if (
      artistPicturePreviewUrl.value &&
      artistPicturePreviewUrl.value.startsWith("blob:")
    ) {
      URL.revokeObjectURL(artistPicturePreviewUrl.value);
    }
    artistPicturePreviewUrl.value = props.initialData.artist_picture || null;
  }
};

const triggerRemovePicture = () => {
  removePicture.value = true;
  artistPictureFile.value = null;
  if (
    artistPicturePreviewUrl.value &&
    artistPicturePreviewUrl.value.startsWith("blob:")
  ) {
    URL.revokeObjectURL(artistPicturePreviewUrl.value);
  }
  artistPicturePreviewUrl.value = null;
};

const handleSubmit = async () => {
  isLoading.value = true;
  emit("updateError", null);

  const submissionData = new FormData();

  submissionData.append("name", formData.value.name || props.initialData.name); // Assuming name can be edited
  submissionData.append("bio", formData.value.bio || "");
  submissionData.append("location", formData.value.location || "");
  submissionData.append("website_url", formData.value.website_url || "");

  if (removePicture.value) {
    submissionData.append("artist_picture", "");
  } else if (artistPictureFile.value) {
    submissionData.append("artist_picture", artistPictureFile.value);
  }

  try {
    const response = await axios.patch(
      `/artists/${props.artistId}/`, // Use artistId from props
      submissionData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    console.log("Artist update successful:", response.data);
    emit("artistUpdated", response.data);
  } catch (error: any) {
    console.error("Artist update failed:", error);
    let errorMessage = "Failed to update artist profile.";
    if (axios.isAxiosError(error) && error.response) {
      const errors = error.response.data;
      if (typeof errors === "object" && errors !== null) {
        errorMessage = Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${(messages as string[]).join(", ")}`
          )
          .join(" | ");
      }
    }
    emit("updateError", errorMessage);
  } finally {
    isLoading.value = false;
  }
};

onUnmounted(() => {
  if (
    artistPicturePreviewUrl.value &&
    artistPicturePreviewUrl.value.startsWith("blob:")
  ) {
    URL.revokeObjectURL(artistPicturePreviewUrl.value);
  }
});
</script>

<template>
  <form @submit.prevent="handleSubmit" class="artist-edit-form">
    <div class="form-group">
      <label for="artist-name-edit">Artist Name:</label>
      <input
        type="text"
        id="artist-name-edit"
        v-model="formData.name"
        required
      />
    </div>
    <div class="form-group">
      <label for="artist-bio">Bio:</label>
      <textarea id="artist-bio" v-model="formData.bio" rows="5"></textarea>
    </div>
    <div class="form-group">
      <label for="artist-location">Location:</label>
      <input type="text" id="artist-location" v-model="formData.location" />
    </div>
    <div class="form-group">
      <label for="artist-website">Website URL:</label>
      <input
        type="url"
        id="artist-website"
        v-model="formData.website_url"
        placeholder="https://example.com"
      />
    </div>
    <div class="form-group">
      <label for="artist-picture">Artist Picture:</label>
      <!-- Preview Area -->
      <div class="preview-area">
        <img
          v-if="artistPicturePreviewUrl"
          :src="artistPicturePreviewUrl"
          alt="Artist picture preview"
          class="artist-pic-preview"
        />
        <div v-else class="artist-pic-placeholder-edit">
          No Picture Selected
        </div>
      </div>
      <input
        type="file"
        id="artist-picture"
        @change="handleFileChange"
        accept="image/jpeg,image/png,image/webp"
      />
      <button
        type="button"
        v-if="artistPicturePreviewUrl"
        @click="triggerRemovePicture"
        class="remove-button"
      >
        {{ removePicture ? "Keeping removal" : "Remove Picture" }}
      </button>
      <p v-if="artistPictureFile" class="file-info">
        New: {{ artistPictureFile.name }}
      </p>
      <p v-if="removePicture" class="file-info">
        Picture will be removed on save.
      </p>
    </div>

    <div class="form-actions">
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Saving..." : "Save Artist Changes" }}
      </button>
      <button type="button" @click="$emit('cancelEdit')" :disabled="isLoading">
        Cancel
      </button>
    </div>
  </form>
</template>

<style scoped>
.artist-edit-form .form-group {
  margin-bottom: 1rem;
  text-align: left;
}
.artist-edit-form label {
  display: block;
  margin-bottom: 0.3rem;
  font-weight: bold;
}
.artist-edit-form input,
.artist-edit-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.artist-edit-form textarea {
  resize: vertical;
}
.artist-edit-form input[type="file"] {
  margin-top: 0.5rem; /* Spacing after preview */
  font-size: 0.9em;
}

/* Styles for Preview Area */
.preview-area {
  margin-bottom: 0.75rem;
  width: 120px;
  height: 120px;
  border: 1px dashed var(--color-border-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  overflow: hidden;
  background-color: var(--color-background-mute);
}
.artist-pic-preview {
  /* Changed class name slightly for clarity if needed */
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.artist-pic-placeholder-edit {
  /* Changed class name slightly */
  font-size: 0.8em;
  color: var(--color-text);
  text-align: center;
}
/* End Preview Area Styles */

.file-info {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text);
  margin-top: 0.2rem;
}
.remove-button {
  font-size: 0.8em;
  padding: 0.2em 0.5em;
  background: none;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  border-radius: 4px;
  margin-left: 1em;
  cursor: pointer;
  vertical-align: middle;
}
.remove-button:hover {
  border-color: red;
  color: red;
}
.form-actions {
  margin-top: 1.5rem;
  display: flex;
  gap: 1rem;
}
.form-actions button {
  padding: 0.7rem 1.5rem;
}
.form-actions button[type="button"] {
  background-color: var(--color-background-mute);
}
</style>
