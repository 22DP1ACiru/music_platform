<script setup lang="ts">
import { ref, watch, type PropType } from "vue";
import axios from "axios";

// Interface for the data needed by the form
interface ArtistFormData {
  name: string; // Name might be editable too? Or maybe not? Decide.
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
    type: String,
    required: true,
  },
});

const emit = defineEmits(["artistUpdated", "cancelEdit", "updateError"]);

// Local state for form fields
const formData = ref<Partial<ArtistFormData>>({ ...props.initialData }); // Use Partial if name isn't editable
const artistPictureFile = ref<File | null>(null);
const isLoading = ref(false);
const removePicture = ref(false); // Flag to signal picture removal

// Reset form if initial data changes
watch(
  () => props.initialData,
  (newData) => {
    formData.value = { ...newData };
    artistPictureFile.value = null;
    removePicture.value = false;
  },
  { deep: true }
);

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    artistPictureFile.value = target.files[0];
    removePicture.value = false; // Selecting a new file cancels removal intent
  } else {
    artistPictureFile.value = null;
  }
};

const triggerRemovePicture = () => {
  removePicture.value = true;
  artistPictureFile.value = null; // Clear any selected file if removing
};

const handleSubmit = async () => {
  isLoading.value = true;
  emit("updateError", null);

  const submissionData = new FormData();

  // Append fields that changed or are required
  // Decide if 'name' is editable. If so, add it:
  // submissionData.append('name', formData.value.name || props.initialData.name);
  submissionData.append("bio", formData.value.bio || "");
  submissionData.append("location", formData.value.location || "");
  submissionData.append("website_url", formData.value.website_url || "");

  // Handle file update/removal
  if (removePicture.value) {
    submissionData.append("artist_picture", ""); // Send empty string to clear
  } else if (artistPictureFile.value) {
    submissionData.append("artist_picture", artistPictureFile.value);
  }
  // If neither flag is set and no file selected, picture is omitted from PATCH

  try {
    // Use PATCH to update the specific artist
    const response = await axios.patch(
      `/artists/${props.artistId}/`,
      submissionData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      }
    );

    console.log("Artist update successful:", response.data);
    emit("artistUpdated", response.data); // Send updated data back
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
</script>

<template>
  <form @submit.prevent="handleSubmit" class="artist-edit-form">
    <!-- Add input for 'name' here if you want it editable -->
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
      <img
        v-if="
          initialData.artist_picture && !artistPictureFile && !removePicture
        "
        :src="initialData.artist_picture"
        alt="Current artist picture"
        class="current-pic"
      />
      <p
        v-if="
          !initialData.artist_picture && !artistPictureFile && !removePicture
        "
      >
        (No current picture)
      </p>
      <input
        type="file"
        id="artist-picture"
        @change="handleFileChange"
        accept="image/*"
      />
      <button
        type="button"
        v-if="initialData.artist_picture || artistPictureFile"
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
  margin-top: 0.3rem;
  font-size: 0.9em;
}
.current-pic {
  max-width: 100px;
  max-height: 100px;
  border-radius: 50%;
  display: block;
  margin-bottom: 0.5rem;
}
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
