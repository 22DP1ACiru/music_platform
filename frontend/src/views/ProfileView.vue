<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink } from "vue-router";
import ProfileEditForm from "@/components/ProfileEditForm.vue";

const authStore = useAuthStore();
const router = useRouter();

const isEditing = ref(false);
const editError = ref<string | null>(null);

// Computed properties to get data from the store
const isLoadingProfile = computed(() => authStore.authLoading); // Use store's loading state
const profileData = computed(() => authStore.authUser?.profile); // Get profile from store
const currentUser = computed(() => authStore.authUser); // Basic user info
const errorLoadingProfile = computed(() => authStore.authError); // Use store's error state

const goToCreateArtist = () => {
  router.push({ name: "artist-create" });
};

const goToCreateRelease = () => {
  if (authStore.hasArtistProfile) {
    router.push({ name: "release-create" });
  } else {
    // This case should ideally be prevented by the button's v-if
    alert("Error: Artist profile required.");
  }
};

// Called when ProfileEditForm emits 'profileUpdated'
const onProfileUpdate = async (updatedProfileDataFromForm: any) => {
  // After a successful PATCH, the backend returns the updated profile.
  // We need to tell the authStore to re-fetch the user/profile data to update its state.
  await authStore.fetchUser(); // Re-fetch to ensure store is up-to-date
  isEditing.value = false;
  editError.value = null;
  alert("Profile updated successfully!");
};

const handleUpdateError = (errorMessage: string | null) => {
  editError.value = errorMessage;
};

// Ensure user/profile data is fetched if not already present when component mounts
onMounted(async () => {
  if (!authStore.authUser || !authStore.authUser.profile) {
    // If profile data is missing in the store, trigger a fetch
    // This handles cases like direct navigation to /profile after login
    // but before fetchUser fully completed or if profile part failed initially.
    await authStore.fetchUser();
  }
});

// Watch for authUser changes if profile might be loaded asynchronously
watch(
  () => authStore.authUser,
  (newUser) => {
    if (newUser && !newUser.profile && !authStore.authLoading) {
      // If user is loaded but profile is missing and not currently loading, try fetching again.
      // This is a fallback, ideally fetchUser in authStore is robust.
      // authStore.fetchUser();
    }
  },
  { immediate: true }
);
</script>

<template>
  <div class="profile-page">
    <h2>Your Profile</h2>

    <div v-if="isLoadingProfile">Loading profile...</div>
    <div v-else-if="errorLoadingProfile" class="error-message">
      {{ errorLoadingProfile }}
    </div>

    <div v-else-if="currentUser && profileData && !isEditing">
      <div class="profile-details">
        <img
          v-if="profileData.profile_picture"
          :src="profileData.profile_picture"
          alt="Profile picture"
          class="profile-pic"
        />
        <div v-else class="profile-pic-placeholder">No Pic</div>

        <p><strong>Username:</strong> {{ currentUser.username }}</p>
        <p v-if="profileData.location">
          <strong>Location:</strong> {{ profileData.location }}
        </p>
        <p v-if="profileData.website_url">
          <strong>Website:</strong>
          <a
            :href="profileData.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ profileData.website_url }}
          </a>
        </p>
        <p v-if="profileData.bio"><strong>Bio:</strong></p>
        <p class="bio-text" v-if="profileData.bio">{{ profileData.bio }}</p>
        <p class="bio-text" v-else>(No bio set)</p>

        <div
          v-if="authStore.hasArtistProfile && profileData.artist_profile_data"
          class="artist-section"
        >
          <div class="artist-link">
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
          <button @click="goToCreateRelease" class="action-button">
            Upload New Release
          </button>
        </div>
        <div
          v-else-if="!authStore.hasArtistProfile"
          class="artist-create-section"
        >
          <p>Ready to share your music?</p>
          <button @click="goToCreateArtist" class="action-button">
            Become an Artist
          </button>
        </div>
      </div>
      <button @click="isEditing = true" class="edit-button action-button">
        Edit Profile
      </button>
    </div>

    <div v-else-if="profileData && isEditing">
      <h3>Edit Profile Details</h3>
      <p v-if="editError" class="error-message">{{ editError }}</p>
      <ProfileEditForm
        :initial-data="{
          bio: profileData.bio,
          location: profileData.location,
          website_url: profileData.website_url,
          profile_picture: profileData.profile_picture,
        }"
        @profile-updated="onProfileUpdate"
        @cancel-edit="
          isEditing = false;
          editError = null;
        "
        @update-error="handleUpdateError"
      />
    </div>

    <div v-else>
      <p>Could not load profile data, or you are not logged in.</p>
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
  white-space: pre-wrap;
  background-color: var(--color-background-soft);
  padding: 0.8rem;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  min-height: 40px;
}

.artist-section,
.artist-create-section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}
.artist-link p {
  margin-bottom: 1rem;
}

.action-button {
  margin-top: 1rem;
  margin-right: 0.5rem;
  padding: 0.6em 1.2em;
}
.edit-button {
  margin-top: 1.5rem;
}
.error-message {
  color: red;
}
</style>
