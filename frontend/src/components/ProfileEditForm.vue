<script setup lang="ts">
import { ref, watch, type PropType } from "vue";
import axios from "axios";

// Define type for initial data prop matching UserProfileData
interface ProfileFormData {
  bio: string | null;
  location: string | null;
  website_url: string | null;
  profile_picture?: string | null; // URL for display, not part of form data sent unless changed
}

// Props received from parent (ProfileView)
const props = defineProps({
  initialData: {
    type: Object as PropType<ProfileFormData>,
    required: true,
  },
});

// Emits to communicate back to parent
const emit = defineEmits(["profileUpdated", "cancelEdit", "updateError"]);

// Local reactive state for form fields, initialized from props
const formData = ref<ProfileFormData>({ ...props.initialData });
const profilePictureFile = ref<File | null>(null); // To hold the selected file object
const removeExistingPicture = ref(false); // Flag to indicate picture removal
const isLoading = ref(false);

// Reset form if initial data changes (e.g., if parent re-fetches)
watch(
  () => props.initialData,
  (newData) => {
    formData.value = { ...newData };
    profilePictureFile.value = null; // Clear selected file on reset
    removeExistingPicture.value = false; // Reset removal flag
  },
  { deep: true }
);

// Handle file input change
const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    profilePictureFile.value = target.files[0];
    removeExistingPicture.value = false; // Selecting a new file cancels removal intent
    console.log("File selected:", profilePictureFile.value);
  } else {
    profilePictureFile.value = null;
  }
};

const triggerRemovePicture = () => {
  removeExistingPicture.value = true;
  profilePictureFile.value = null; // Clear any selected file if removing
};

// Handle form submission
const handleSubmit = async () => {
  isLoading.value = true;
  emit("updateError", null); // Clear previous errors in parent

  const submissionData = new FormData();

  submissionData.append("bio", formData.value.bio || "");
  submissionData.append("location", formData.value.location || "");
  submissionData.append("website_url", formData.value.website_url || "");

  if (removeExistingPicture.value) {
    submissionData.append("profile_picture", ""); // Send empty string to clear (backend must handle this)
  } else if (profilePictureFile.value) {
    submissionData.append("profile_picture", profilePictureFile.value);
  }
  // If no new file and not removing, picture is omitted from PATCH, backend keeps existing.

  try {
    const response = await axios.patch("/profiles/me/", submissionData, {
      // headers: { 'Content-Type': 'multipart/form-data' } // Axios usually handles this for FormData
    });

    console.log("Profile update successful:", response.data);
    emit("profileUpdated", response.data);
  } catch (error: any) {
    console.error("Profile update failed:", error);
    let errorMessage = "Failed to update profile.";
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
  <form @submit.prevent="handleSubmit" class="profile-edit-form">
    <div class="form-group">
      <label for="profile-bio">Bio:</label>
      <textarea id="profile-bio" v-model="formData.bio" rows="4"></textarea>
    </div>
    <div class="form-group">
      <label for="profile-location">Location:</label>
      <input type="text" id="profile-location" v-model="formData.location" />
    </div>
    <div class="form-group">
      <label for="profile-website">Website URL:</label>
      <input
        type="url"
        id="profile-website"
        v-model="formData.website_url"
        placeholder="https://example.com"
      />
    </div>
    <div class="form-group">
      <label for="profile-picture">Profile Picture:</label>
      <img
        v-if="
          initialData.profile_picture &&
          !profilePictureFile &&
          !removeExistingPicture
        "
        :src="initialData.profile_picture"
        alt="Current profile picture"
        class="current-profile-pic"
      />
      <p
        v-if="
          !initialData.profile_picture &&
          !profilePictureFile &&
          !removeExistingPicture
        "
      >
        (No current picture)
      </p>
      <input
        type="file"
        id="profile-picture"
        @change="handleFileChange"
        accept="image/*"
      />
      <button
        type="button"
        v-if="initialData.profile_picture || profilePictureFile"
        @click="triggerRemovePicture"
        class="remove-button"
        :disabled="isLoading"
      >
        {{ removeExistingPicture ? "Keeping removal" : "Remove Picture" }}
      </button>
      <p v-if="profilePictureFile" class="file-info">
        New: {{ profilePictureFile.name }}
      </p>
      <p v-if="removeExistingPicture && !profilePictureFile" class="file-info">
        Current picture will be removed on save.
      </p>
    </div>

    <div class="form-actions">
      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Saving..." : "Save Changes" }}
      </button>
      <button type="button" @click="$emit('cancelEdit')" :disabled="isLoading">
        Cancel
      </button>
    </div>
  </form>
</template>

<style scoped>
.profile-edit-form .form-group {
  margin-bottom: 1.5rem;
  text-align: left;
}
.profile-edit-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: bold;
}
.profile-edit-form input[type="text"],
.profile-edit-form input[type="url"],
.profile-edit-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.profile-edit-form textarea {
  resize: vertical;
}
.profile-edit-form input[type="file"] {
  margin-top: 0.5rem;
  font-size: 0.9em;
}
.current-profile-pic {
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
  margin-top: 2rem;
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