<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

// --- Define Form Data Ref ---
const artistName = ref("");
const artistBio = ref("");
const artistLocation = ref(""); // Added location
const artistWebsite = ref(""); // Added website
const artistPictureFile = ref<File | null>(null); // For file upload
// -----------------------------

const isLoading = ref(false);
const error = ref<string | null>(null);
const router = useRouter();
// const authStore = useAuthStore(); // If needed later

const handleFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files[0]) {
    artistPictureFile.value = target.files[0];
  } else {
    artistPictureFile.value = null;
  }
};

const handleSubmit = async () => {
  isLoading.value = true;
  error.value = null;

  // Use FormData for file upload
  const formData = new FormData();
  formData.append("name", artistName.value);
  formData.append("bio", artistBio.value || ""); // Send empty string if null/undefined
  formData.append("location", artistLocation.value || "");
  formData.append("website_url", artistWebsite.value || "");
  if (artistPictureFile.value) {
    formData.append("artist_picture", artistPictureFile.value);
  }

  try {
    // Interceptor adds auth token
    const response = await axios.post("/artists/", formData, {
      headers: { "Content-Type": "multipart/form-data" }, // Important for files
    });

    console.log("Artist profile created:", response.data);
    alert("Artist profile created successfully!");

    // Redirect to the new artist's detail page or the user's profile
    // Need the ID from the response
    const newArtistId = response.data.id;
    if (newArtistId) {
      router.push({ name: "artist-detail", params: { id: newArtistId } });
    } else {
      router.push({ name: "profile" }); // Fallback to user profile
    }
    // Optional: Force refresh profile data in store if needed
    // await authStore.fetchUser(); // If artist link is part of user data
  } catch (err: any) {
    console.error("Failed to create artist profile:", err);
    if (axios.isAxiosError(err) && err.response) {
      const errors = err.response.data;
      if (typeof errors === "object" && errors !== null) {
        // Display backend validation errors
        error.value = Object.entries(errors)
          .map(
            ([field, messages]) =>
              `${field}: ${(messages as string[]).join(", ")}`
          )
          .join(" | ");
      } else {
        error.value = `Error (${err.response.status}): Failed to create profile.`;
      }
    } else {
      error.value = "An unexpected error occurred.";
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<template>
  <div class="create-artist-page">
    <h2>Create Your Artist Profile</h2>
    <p>Set up your public artist identity on Vaultwave.</p>

    <form @submit.prevent="handleSubmit" class="artist-form">
      <div class="form-group">
        <label for="artist-name">Artist/Band Name:</label>
        <input type="text" id="artist-name" v-model="artistName" required />
      </div>
      <div class="form-group">
        <label for="artist-bio">Bio:</label>
        <textarea id="artist-bio" v-model="artistBio" rows="5"></textarea>
      </div>
      <div class="form-group">
        <label for="artist-location">Location:</label>
        <input type="text" id="artist-location" v-model="artistLocation" />
      </div>
      <div class="form-group">
        <label for="artist-website">Website URL:</label>
        <input
          type="url"
          id="artist-website"
          v-model="artistWebsite"
          placeholder="https://example.com"
        />
      </div>
      <div class="form-group">
        <label for="artist-picture">Artist Picture:</label>
        <input
          type="file"
          id="artist-picture"
          @change="handleFileChange"
          accept="image/*"
        />
        <p v-if="artistPictureFile" class="file-info">
          Selected: {{ artistPictureFile.name }}
        </p>
      </div>

      <div v-if="error" class="error-message">{{ error }}</div>

      <button type="submit" :disabled="isLoading">
        {{ isLoading ? "Creating..." : "Create Artist Profile" }}
      </button>
      <button
        type="button"
        @click="router.push({ name: 'profile' })"
        :disabled="isLoading"
        class="cancel-button"
      >
        Cancel
      </button>
    </form>
  </div>
</template>

<style scoped>
.create-artist-page {
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.create-artist-page h2 {
  margin-bottom: 0.5rem;
}
.create-artist-page p {
  margin-bottom: 1.5rem;
  color: var(--color-text);
}
.artist-form .form-group {
  margin-bottom: 1rem;
  text-align: left;
}
.artist-form label {
  display: block;
  margin-bottom: 0.3rem;
  font-weight: bold;
}
.artist-form input[type="text"],
.artist-form input[type="url"],
.artist-form textarea {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1em;
}
.artist-form textarea {
  resize: vertical;
}
.artist-form input[type="file"] {
  margin-top: 0.3rem;
  font-size: 0.9em;
}
.file-info {
  font-size: 0.85em;
  font-style: italic;
  color: var(--color-text);
  margin-top: 0.2rem;
}
.error-message {
  color: red;
  margin-bottom: 1rem;
}
button {
  margin-right: 1rem;
  margin-top: 1rem;
}
.cancel-button {
  background-color: var(--color-background-mute);
}
</style>
