// frontend/src/views/profile/ProfileView.vue
<script setup lang="ts">
import { ref, onMounted, computed, watch } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink, useRoute } from "vue-router";
import ProfileEditForm from "@/components/profile/ProfileEditForm.vue";
import { useChatStore } from "@/stores/chat";
import ChooseSenderIdentityModal from "@/components/chat/ChooseSenderIdentityModal.vue";
import axios from "axios";

const props = defineProps<{
  userIdToShow?: string | null;
}>();

const authStore = useAuthStore();
const chatStore = useChatStore();
const router = useRouter();
const route = useRoute();

const isEditing = ref(false);
const editError = ref<string | null>(null);
const showIdentityModal = ref(false);

const displayedUser = ref<ReturnType<typeof authStore.authUser>>(null);
const displayedProfile =
  ref<ReturnType<typeof authStore.authUser>["value"]["profile"]>(null);

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
    if (!authStore.isLoggedIn) router.push({ name: "login" });
    errorLoadingDisplayedProfile.value = "No user to display.";
    return;
  }

  isLoadingDisplayedProfile.value = true;
  errorLoadingDisplayedProfile.value = null;

  if (targetUserId === authStore.authUser?.id) {
    if (!authStore.authUser || !authStore.authUser.profile) {
      await authStore.fetchUser();
    }
    displayedUser.value = authStore.authUser;
    displayedProfile.value = authStore.authUser?.profile || null;
  } else {
    try {
      const userRes = await axios.get(`/users/${targetUserId}/`);
      if (userRes.data.profile) {
        displayedProfile.value = userRes.data.profile;
      } else {
        const profileResponse = await axios.get(
          `/profiles/?user_id=${targetUserId}`
        );
        if (profileResponse.data && profileResponse.data.length > 0) {
          displayedProfile.value = profileResponse.data[0];
        } else {
          displayedProfile.value = null;
        }
      }
      displayedUser.value = userRes.data;
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
    if (
      convo.initiator_user?.id === authStore.authUser!.id &&
      convo.initiator_identity_type === chosenSenderIdentity &&
      (chosenSenderIdentity === "ARTIST"
        ? convo.initiator_artist_profile_details?.id === senderArtistProfileId
        : true) &&
      !convo.related_artist_recipient_details &&
      convo.participants.some(
        (p) =>
          p.id === displayedUser.value!.id && p.id !== authStore.authUser!.id
      )
    )
      return true;
    if (
      convo.initiator_user?.id === displayedUser.value!.id &&
      convo.initiator_identity_type === "USER" &&
      !convo.related_artist_recipient_details &&
      (chosenSenderIdentity === "USER"
        ? !convo.related_artist_recipient_details
        : convo.related_artist_recipient_details?.id === senderArtistProfileId)
    )
      return true;
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

    <div v-else-if="displayedUser && !isEditing">
      <div class="profile-details">
        <img
          v-if="displayedProfile?.profile_picture"
          :src="getFullImageUrl(displayedProfile.profile_picture)"
          alt="Profile picture"
          class="profile-pic"
        />
        <div v-else class="profile-pic-placeholder">No Pic</div>

        <p><strong>Username:</strong> {{ displayedUser.username }}</p>
        <p v-if="displayedProfile?.location">
          <strong>Location:</strong> {{ displayedProfile.location }}
        </p>
        <p v-if="displayedProfile?.website_url">
          <strong>Website:</strong>
          <a
            :href="displayedProfile.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ displayedProfile.website_url }}
          </a>
        </p>
        <p v-if="displayedProfile?.bio"><strong>Bio:</strong></p>
        <p class="bio-text" v-if="displayedProfile?.bio">
          {{ displayedProfile.bio }}
        </p>
        <p class="bio-text" v-else>(No bio set)</p>

        <button
          v-if="authStore.isLoggedIn && !isMyOwnProfile"
          @click="startChatWithDisplayedUser"
          class="action-button send-message-button"
        >
          Send Message to {{ displayedUser.username }}
        </button>

        <div v-if="isMyOwnProfile">
          <div class="user-actions-section">
            <RouterLink
              :to="{ name: 'user-listening-habits' }"
              class="action-button"
            >
              View My Listening Habits
            </RouterLink>
          </div>

          <div
            v-if="
              authStore.hasArtistProfile &&
              displayedProfile?.artist_profile_data
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

    <div v-else-if="!isLoadingDisplayedProfile && !displayedUser">
      <p>Could not load profile data for this user.</p>
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
  padding: 1rem;
  background-color: var(--color-background);
  border-radius: 6px;
  /* border: 1px solid var(--color-border); Optional: if you want a border around view mode */
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

.user-actions-section, /* New class for styling user-specific action links */
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
  text-decoration: none; /* Ensure RouterLink as button looks like button */
  display: inline-block; /* For RouterLink as button */
  border-radius: 4px;
  cursor: pointer;
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border: 1px solid var(--color-accent);
}
.action-button:hover {
  background-color: var(--color-accent-hover);
}

.edit-button {
  margin-top: 1.5rem;
  background-color: var(--color-background-soft); /* Different style for edit */
  color: var(--color-text);
  border-color: var(--color-border);
}
.edit-button:hover {
  border-color: var(--color-border-hover);
  background-color: var(--color-background-mute);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.75rem;
  border-radius: 4px;
  margin: 1rem 0;
}
.send-message-button {
  /* background-color: var(--color-accent);
  color: white; */
  margin-top: 1rem;
  /* border: 1px solid var(--color-accent); */
}
/* .send-message-button:hover {
  background-color: var(--color-accent-hover);
} */
</style>
