<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import axios from "axios";
import { useAuthStore } from "@/stores/auth"; // Use Pinia store
import { useRouter, RouterLink } from "vue-router";
import ProfileEditForm from "@/components/ProfileEditForm.vue";

// Define interface for the profile data fetched from API
// Should match UserProfileSerializer + nested artist data
interface ArtistProfileData {
  id: number;
  name: string;
  // Add other fields from ArtistSerializer if needed
}
interface UserProfileData {
  id: number;
  user: string; // Username from StringRelatedField
  bio: string | null;
  profile_picture: string | null; // URL
  location: string | null;
  website_url: string | null;
  artist_profile_data: ArtistProfileData | null; // Nested artist info or null
}

const authStore = useAuthStore();
const profileData = ref<UserProfileData | null>(null);
const isLoading = ref(true);
const error = ref<string | null>(null);
const isEditing = ref(false); // State to control edit mode
const editError = ref<string | null>(null);

const router = useRouter();

// Get base user info from the store (username, email)
const currentUser = computed(() => authStore.authUser);

const goToCreateArtist = () => {
  router.push({ name: "artist-create" });
};

const fetchProfile = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    // Interceptor adds token
    const response = await axios.get<UserProfileData>("/profiles/me/");
    profileData.value = response.data;
    console.log("Fetched profile data:", profileData.value);
  } catch (err) {
    console.error("Failed to fetch profile:", err);
    error.value = "Could not load your profile.";
    // Handle specific errors like 404 if profile wasn't auto-created
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value =
        "Profile not found. Please contact support or try creating one."; // Or potentially auto-create here?
    }
  } finally {
    isLoading.value = false;
  }
};

// Function to call after successful edit (to refresh displayed data)
const onProfileUpdate = (updatedProfileData: any) => {
  if (updatedProfileData) {
    profileData.value = updatedProfileData; // If API returns full profile
  }
  isEditing.value = false; // Exit edit mode
  editError.value = null; // Clear edit errors
  alert("Profile updated successfully!");
};

const handleUpdateError = (errorMessage: string | null) => {
  editError.value = errorMessage;
};

// Fetch profile when component mounts
onMounted(fetchProfile);
</script>

<template>
  <div class="profile-page">
    <h2>Your Profile</h2>

    <div v-if="isLoading">Loading profile...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <!-- Display Mode -->
    <div v-else-if="profileData && !isEditing">
      <div class="profile-details">
        <img
          v-if="profileData.profile_picture"
          :src="profileData.profile_picture"
          alt="Profile picture"
          class="profile-pic"
        />
        <div v-else class="profile-pic-placeholder">No Pic</div>

        <p><strong>Username:</strong> {{ currentUser?.username }}</p>
        <p v-if="profileData.location">
          <strong>Location:</strong> {{ profileData.location }}
        </p>
        <p v-if="profileData.website_url">
          <strong>Website:</strong>
          <a
            v-if="profileData.website_url"
            :href="profileData.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ profileData.website_url }}
          </a>
          <span v-else>Not set</span>
        </p>
        <p v-if="profileData.bio"><strong>Bio:</strong></p>
        <p class="bio-text">{{ profileData.bio }}</p>

        <!-- Artist Profile Link -->
        <div v-if="profileData.artist_profile_data" class="artist-link">
          <p>
            <strong>Artist Profile:</strong>
            <RouterLink
              :to="{
                name: 'artist-detail',
                params: { id: profileData.artist_profile_data.id },
              }"
            >
              {{ profileData.artist_profile_data.name }}
            </RouterLink>
          </p>
        </div>
        <div v-else class="artist-create-section">
          <p>Ready to share your music?</p>
          <button @click="goToCreateArtist">Become an Artist</button>
        </div>
      </div>
      <button @click="isEditing = true" class="edit-button">
        Edit Profile
      </button>
    </div>

    <!-- Edit Mode (Placeholder for now) -->
    <div v-else-if="profileData && isEditing">
      <h3>Edit Profile</h3>
      <!-- Display edit errors -->
      <p v-if="editError" class="error-message">{{ editError }}</p>
      <ProfileEditForm
        :initial-data="profileData"
        @profile-updated="onProfileUpdate"
        @cancel-edit="
          isEditing = false;
          editError = null;
        "
        @update-error="handleUpdateError"
      />
    </div>

    <div v-else>
      <p>Could not load profile data.</p>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 700px;
  margin: 2rem auto;
}
.profile-details {
  text-align: left;
  line-height: 1.8;
}
.profile-pic,
.profile-pic-placeholder {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  object-fit: cover;
  margin-bottom: 1.5rem;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.profile-details p {
  margin-bottom: 0.8rem;
}
.bio-text {
  white-space: pre-wrap; /* Respect line breaks in bio */
  background-color: var(--color-background-soft);
  padding: 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-border);
}
.artist-link {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}
.edit-button,
.profile-page button {
  margin-top: 1.5rem;
}
.error-message {
  color: red;
}
</style>
