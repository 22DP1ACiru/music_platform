<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import {
  useRouter,
  RouterLink,
  useRoute, // Added useRoute
} from "vue-router";
import ProfileEditForm from "@/components/ProfileEditForm.vue";
import { useChatStore } from "@/stores/chat";
import ChooseSenderIdentityModal from "@/components/chat/ChooseSenderIdentityModal.vue"; // Import the modal

// Hypothetical prop if this view could show other users' profiles
const props = defineProps<{
  userIdToShow?: string | null; // ID of the profile being viewed, if not 'me'
}>();

const authStore = useAuthStore();
const chatStore = useChatStore();
const router = useRouter();
const route = useRoute(); // For current route info

const isEditing = ref(false);
const editError = ref<string | null>(null);
const showIdentityModal = ref(false);

// This will hold the profile data being displayed (either 'me' or another user)
const displayedUser = ref<ReturnType<typeof authStore.authUser>>(null); // Using the type from authUser
const displayedProfile =
  ref<ReturnType<typeof authStore.authUser>["value"]["profile"]>(null); // Using the type from authUser.profile

const isLoadingDisplayedProfile = ref(false);
const errorLoadingDisplayedProfile = ref<string | null>(null);

const isMyOwnProfile = computed(() => {
  if (!authStore.isLoggedIn || !displayedUser.value) return false;
  return displayedUser.value.id === authStore.authUser?.id;
});

async function fetchProfileData() {
  const targetUserId = props.userIdToShow
    ? parseInt(props.userIdToShow)
    : authStore.authUser?.id;

  if (!targetUserId) {
    // If not logged in and no userIdToShow, can't load anything
    if (!authStore.isLoggedIn) router.push({ name: "login" });
    errorLoadingDisplayedProfile.value = "No user to display.";
    return;
  }

  isLoadingDisplayedProfile.value = true;
  errorLoadingDisplayedProfile.value = null;

  if (targetUserId === authStore.authUser?.id) {
    // Fetching own profile (or ensuring it's loaded from store)
    if (!authStore.authUser || !authStore.authUser.profile) {
      await authStore.fetchUser(); // Ensure full user data is loaded
    }
    displayedUser.value = authStore.authUser;
    displayedProfile.value = authStore.authUser?.profile || null;
  } else {
    // Fetching another user's profile
    try {
      // You'll need an endpoint like /api/users/:id/profile-details/ or similar
      // that returns both User (username, id) and UserProfile data.
      // For now, let's assume two separate calls or a combined one.
      const userRes = await axios.get(`/users/${targetUserId}/`); // Basic user data
      const profileRes = await axios.get(`/profiles/${targetUserId}/public/`); // Hypothetical public profile endpoint

      displayedUser.value = userRes.data;
      displayedProfile.value = profileRes.data;
    } catch (err) {
      console.error("Failed to fetch public profile data:", err);
      errorLoadingDisplayedProfile.value =
        "Could not load this user's profile.";
      displayedUser.value = null;
      displayedProfile.value = null;
    }
  }
  isLoadingDisplayedProfile.value = false;
}

const onProfileUpdate = async (updatedProfileDataFromForm: any) => {
  await authStore.fetchUser();
  isEditing.value = false;
  editError.value = null;
  alert("Profile updated successfully!");
  // Re-fetch displayed profile if it was 'me'
  if (isMyOwnProfile.value) {
    displayedProfile.value = authStore.authUser?.profile || null;
  }
};

const handleUpdateError = (errorMessage: string | null) => {
  editError.value = errorMessage;
};

const proceedWithChatToUser = (chosenSenderIdentity: "USER" | "ARTIST") => {
  if (!displayedUser.value || !authStore.authUser) return;

  const senderArtistProfileId =
    chosenSenderIdentity === "ARTIST" ? authStore.artistProfileId : null;

  const existingConversation = chatStore.conversations.find((convo) => {
    const participantIds = convo.participants.map((p) => p.id);
    const involvesMe = participantIds.includes(authStore.authUser!.id);
    const involvesTargetUser = participantIds.includes(displayedUser.value!.id);

    if (!(involvesMe && involvesTargetUser && participantIds.length === 2))
      return false;

    // Check if I (with chosenSenderIdentity) initiated to this user
    if (
      convo.initiator_user?.id === authStore.authUser!.id &&
      convo.initiator_identity_type === chosenSenderIdentity &&
      (chosenSenderIdentity === "ARTIST"
        ? convo.initiator_artist_profile_details?.id === senderArtistProfileId
        : true) &&
      !convo.related_artist_recipient_details && // Target is a USER
      convo.participants.some(
        (p) =>
          p.id === displayedUser.value!.id && p.id !== authStore.authUser!.id
      ) // Target user is the other participant
    ) {
      return true;
    }
    // Check if this user initiated to me (with chosenSenderIdentity)
    if (
      convo.initiator_user?.id === displayedUser.value!.id && // Target user initiated
      convo.initiator_identity_type === "USER" && // As user
      !convo.related_artist_recipient_details && // To me as user (not my artist profile)
      (chosenSenderIdentity === "USER"
        ? !convo.related_artist_recipient_details
        : convo.related_artist_recipient_details?.id === senderArtistProfileId) // I am receiving as chosen identity
    ) {
      return true;
    }
    return false;
  });

  if (existingConversation) {
    router.push({
      name: "chat-conversation",
      params: { conversationId: existingConversation.id.toString() },
    });
  } else {
    const queryParams: any = {
      recipientUserId: displayedUser.value.id.toString(),
      senderIdentity: chosenSenderIdentity,
    };
    if (chosenSenderIdentity === "ARTIST" && senderArtistProfileId) {
      queryParams.senderArtistProfileId = senderArtistProfileId.toString();
    }
    router.push({
      name: "chat-conversation",
      params: { conversationId: "new" },
      query: queryParams,
    });
  }
  showIdentityModal.value = false;
};

const startChatWithDisplayedUser = () => {
  if (!displayedUser.value || !authStore.isLoggedIn || !authStore.authUser) {
    alert("Error: Cannot determine recipient or sender.");
    return;
  }
  if (displayedUser.value.id === authStore.authUser.id) {
    alert("You cannot send a message to yourself.");
    return;
  }

  if (authStore.hasArtistProfile) {
    showIdentityModal.value = true;
  } else {
    proceedWithChatToUser("USER");
  }
};

onMounted(() => {
  fetchProfileData();
  if (authStore.isLoggedIn && chatStore.conversations.length === 0) {
    chatStore.fetchConversations();
  }
});

watch(
  () => props.userIdToShow,
  () => {
    fetchProfileData();
  },
  { immediate: true }
);

watch(
  () => authStore.authUser,
  (newUser, oldUser) => {
    if (isMyOwnProfile.value || !props.userIdToShow) {
      // If viewing own profile, or if no specific user ID prop
      if (newUser && (!oldUser || newUser.profile !== oldUser.profile)) {
        displayedUser.value = newUser;
        displayedProfile.value = newUser.profile || null;
      } else if (!newUser) {
        displayedUser.value = null;
        displayedProfile.value = null;
      }
    }
  },
  { deep: true }
);
</script>

<template>
  <div class="profile-page">
    <h2 v-if="isMyOwnProfile">Your Profile</h2>
    <h2 v-else-if="displayedUser">Profile: {{ displayedUser.username }}</h2>
    <h2 v-else>Profile</h2>

    <div v-if="isLoadingDisplayedProfile">Loading profile...</div>
    <div v-else-if="errorLoadingDisplayedProfile" class="error-message">
      {{ errorLoadingDisplayedProfile }}
    </div>

    <div v-else-if="displayedUser && displayedProfile && !isEditing">
      <div class="profile-details">
        <img
          v-if="displayedProfile.profile_picture"
          :src="displayedProfile.profile_picture"
          alt="Profile picture"
          class="profile-pic"
        />
        <div v-else class="profile-pic-placeholder">No Pic</div>

        <p><strong>Username:</strong> {{ displayedUser.username }}</p>
        <p v-if="displayedProfile.location">
          <strong>Location:</strong> {{ displayedProfile.location }}
        </p>
        <p v-if="displayedProfile.website_url">
          <strong>Website:</strong>
          <a
            :href="displayedProfile.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ displayedProfile.website_url }}
          </a>
        </p>
        <p v-if="displayedProfile.bio"><strong>Bio:</strong></p>
        <p class="bio-text" v-if="displayedProfile.bio">
          {{ displayedProfile.bio }}
        </p>
        <p class="bio-text" v-else>(No bio set)</p>

        <!-- "Send Message" button appears if viewing another user's profile -->
        <button
          v-if="authStore.isLoggedIn && !isMyOwnProfile"
          @click="startChatWithDisplayedUser"
          class="action-button send-message-button"
        >
          Send Message to {{ displayedUser.username }}
        </button>

        <!-- Artist specific section for own profile -->
        <div v-if="isMyOwnProfile">
          <div
            v-if="
              authStore.hasArtistProfile && displayedProfile.artist_profile_data
            "
            class="artist-section"
          >
            <div class="artist-link">
              <p>
                <strong>Artist Profile:</strong>
                <RouterLink
                  :to="{
                    name: 'artist-detail',
                    params: { id: displayedProfile.artist_profile_data.id },
                  }"
                >
                  {{ displayedProfile.artist_profile_data.name }}
                </RouterLink>
              </p>
            </div>
            <RouterLink
              :to="{ name: 'release-create' }"
              custom
              v-slot="{ navigate }"
            >
              <button @click="navigate" class="action-button">
                Upload New Release
              </button>
            </RouterLink>
          </div>
          <div
            v-else-if="!authStore.hasArtistProfile"
            class="artist-create-section"
          >
            <p>Ready to share your music?</p>
            <RouterLink
              :to="{ name: 'artist-create' }"
              custom
              v-slot="{ navigate }"
            >
              <button @click="navigate" class="action-button">
                Become an Artist
              </button>
            </RouterLink>
          </div>
        </div>
      </div>
      <button
        v-if="isMyOwnProfile"
        @click="isEditing = true"
        class="edit-button action-button"
      >
        Edit My Profile
      </button>
    </div>

    <div v-else-if="displayedProfile && isEditing && isMyOwnProfile">
      <h3>Edit Profile Details</h3>
      <p v-if="editError" class="error-message">{{ editError }}</p>
      <ProfileEditForm
        :initial-data="{
          bio: displayedProfile.bio,
          location: displayedProfile.location,
          website_url: displayedProfile.website_url,
          profile_picture: displayedProfile.profile_picture,
        }"
        @profile-updated="onProfileUpdate"
        @cancel-edit="
          isEditing = false;
          editError = null;
        "
        @update-error="handleUpdateError"
      />
    </div>

    <div v-else-if="!isLoadingDisplayedProfile">
      <p>Could not load profile data.</p>
    </div>

    <ChooseSenderIdentityModal
      :is-visible="showIdentityModal"
      @identity-chosen="proceedWithChatToUser"
      @close="showIdentityModal = false"
    />
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
.send-message-button {
  background-color: var(--color-accent);
  color: white;
  margin-top: 1rem;
  border: 1px solid var(--color-accent);
}
.send-message-button:hover {
  background-color: var(--color-accent-hover);
}
</style>
