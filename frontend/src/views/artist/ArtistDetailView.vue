<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { RouterLink, useRouter, useRoute } from "vue-router"; // Added useRoute
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import { useInteractionsStore } from "@/stores/interactions"; // Import interactions store
import ArtistEditForm from "@/components/artist/ArtistEditForm.vue";
import { useChatStore } from "@/stores/chat";
import type { Conversation } from "@/types";
import ChooseSenderIdentityModal from "@/components/chat/ChooseSenderIdentityModal.vue";

interface ArtistDetail {
  id: number;
  name: string;
  bio: string | null;
  artist_picture: string | null;
  location: string | null;
  website_url: string | null;
  user: string;
  user_id: number;
}

interface ReleaseSummary {
  id: number;
  title: string;
  cover_art: string | null;
  release_type: string;
  release_type_display?: string;
}

interface PaginatedArtistReleasesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ReleaseSummary[];
}

const props = defineProps<{
  id: string;
}>();

const authStore = useAuthStore();
const interactionsStore = useInteractionsStore(); // Use interactions store
const chatStore = useChatStore();
const router = useRouter();
const route = useRoute(); // For redirect query on login for chat
const artist = ref<ArtistDetail | null>(null);
const releases = ref<ReleaseSummary[]>([]);
const isLoadingArtist = ref(true);
const isLoadingReleases = ref(true);
const error = ref<string | null>(null);
const isEditing = ref(false);
const editError = ref<string | null>(null);

const showIdentityModal = ref(false);

const isOwner = computed(() => {
  return (
    authStore.isLoggedIn &&
    authStore.authUser &&
    artist.value &&
    artist.value.user_id === authStore.authUser.id
  );
});

// Renamed from isMyArtistProfile to avoid confusion with isOwner
const isViewingOwnArtistProfile = computed(() => {
  return (
    authStore.isLoggedIn && authStore.artistProfileId === parseInt(props.id, 10)
  );
});

// --- Follow/Unfollow Logic ---
const currentArtistId = computed(() => artist.value?.id);

const isFollowing = computed(() => {
  if (currentArtistId.value === undefined) return false;
  return interactionsStore.getFollowingStatus(currentArtistId.value) || false;
});

const isLoadingFollowStatus = computed(() => {
  if (currentArtistId.value === undefined) return false;
  return interactionsStore.getIsLoadingStatus(currentArtistId.value);
});

const isLoadingFollowAction = computed(() => {
  if (currentArtistId.value === undefined) return false;
  return interactionsStore.getIsLoadingAction(currentArtistId.value);
});

const followButtonText = computed(() => {
  if (isLoadingFollowStatus.value) return "Loading...";
  if (isLoadingFollowAction.value)
    return isFollowing.value ? "Unfollowing..." : "Following...";
  return isFollowing.value ? "Unfollow" : "Follow";
});

const handleFollowToggle = async () => {
  if (!authStore.isLoggedIn) {
    router.push({ name: "login", query: { redirect: route.fullPath } });
    return;
  }
  if (currentArtistId.value === undefined || isLoadingFollowAction.value)
    return;

  if (isFollowing.value) {
    await interactionsStore.unfollowArtist(currentArtistId.value);
  } else {
    await interactionsStore.followArtist(currentArtistId.value);
  }
  // Error handling can be done by observing interactionsStore.error if needed
};
// --- End Follow/Unfollow Logic ---

const fetchArtistDetail = async (artistId: string) => {
  isLoadingArtist.value = true;
  error.value = null;
  artist.value = null;
  try {
    const response = await axios.get<ArtistDetail>(`/artists/${artistId}/`);
    artist.value = response.data;
    if (artist.value && authStore.isLoggedIn && !isOwner.value) {
      // Check follow status if logged in and not owner
      interactionsStore.checkFollowingStatus(artist.value.id);
    }
  } catch (err: any) {
    console.error(`Failed to fetch artist ${artistId}:`, err);
    if (axios.isAxiosError(err) && err.response?.status === 404) {
      error.value = "Artist not found.";
    } else {
      error.value = "Could not load artist details.";
    }
  } finally {
    isLoadingArtist.value = false;
  }
};

const fetchArtistReleases = async (artistId: string) => {
  isLoadingReleases.value = true;
  releases.value = [];
  try {
    const response = await axios.get<PaginatedArtistReleasesResponse>(
      `/releases/?artist=${artistId}`
    );
    releases.value = response.data.results;
  } catch (err) {
    console.error(`Failed to fetch releases for artist ${artistId}:`, err);
  } finally {
    isLoadingReleases.value = false;
  }
};

const loadData = (artistId: string) => {
  if (artistId) {
    fetchArtistDetail(artistId);
    fetchArtistReleases(artistId);
  } else {
    error.value = "Invalid Artist ID.";
    isLoadingArtist.value = false;
    isLoadingReleases.value = false;
  }
};

const onArtistUpdate = (updatedArtistData: ArtistDetail) => {
  artist.value = { ...artist.value, ...updatedArtistData };
  isEditing.value = false;
  editError.value = null;
  alert("Artist profile updated successfully!");
};

const handleUpdateError = (errorMessage: string | null) => {
  editError.value = errorMessage;
};

const proceedWithChatNavigation = (chosenSenderIdentity: "USER" | "ARTIST") => {
  if (!artist.value || !authStore.authUser) return;

  const senderArtistProfileId =
    chosenSenderIdentity === "ARTIST" ? authStore.artistProfileId : null;

  const existingConversation = chatStore.conversations.find((convo) => {
    const participantIds = convo.participants.map((p) => p.id);
    const involvesMe = participantIds.includes(authStore.authUser!.id);
    const involvesTargetUserAsArtistOwner = participantIds.includes(
      artist.value!.user_id
    );

    if (
      !(
        involvesMe &&
        involvesTargetUserAsArtistOwner &&
        participantIds.length === 2
      )
    )
      return false;

    if (convo.initiator_user?.id === authStore.authUser!.id) {
      return (
        convo.initiator_identity_type === chosenSenderIdentity &&
        (chosenSenderIdentity === "ARTIST"
          ? convo.initiator_artist_profile_details?.id === senderArtistProfileId
          : true) &&
        convo.related_artist_recipient_details?.id === artist.value!.id
      );
    }
    if (convo.initiator_user?.id === artist.value!.user_id) {
      if (
        convo.initiator_identity_type === "ARTIST" &&
        convo.initiator_artist_profile_details?.id === artist.value!.id
      ) {
        if (
          chosenSenderIdentity === "USER" &&
          convo.related_artist_recipient_details === null
        )
          return true;
        if (
          chosenSenderIdentity === "ARTIST" &&
          convo.related_artist_recipient_details?.id === senderArtistProfileId
        )
          return true;
      } else if (
        convo.initiator_identity_type === "USER" &&
        chosenSenderIdentity === "USER" &&
        convo.related_artist_recipient_details?.id === artist.value!.id
      ) {
        return true;
      }
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
      recipientArtistId: artist.value.id.toString(),
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

const startChatWithArtist = async () => {
  if (!artist.value || !authStore.isLoggedIn || !authStore.authUser) {
    alert("You need to be logged in to send a message.");
    router.push({
      name: "login",
      query: { redirect: router.currentRoute.value.fullPath },
    });
    return;
  }
  // Cannot send a message TO your own artist profile via this button
  // This is slightly different from the `isOwner` check for editing,
  // as this refers to the *target* of the message.
  if (artist.value.id === authStore.artistProfileId) {
    alert(
      "You cannot send a message to your own artist profile page using this button."
    );
    return;
  }

  if (authStore.hasArtistProfile) {
    showIdentityModal.value = true;
  } else {
    proceedWithChatNavigation("USER");
  }
};

onMounted(() => {
  loadData(props.id);
  if (authStore.isLoggedIn && chatStore.conversations.length === 0) {
    chatStore.fetchConversations();
  }
});

watch(
  () => props.id,
  (newId) => {
    loadData(newId);
  }
);
</script>

<template>
  <div class="artist-detail-page">
    <div v-if="isLoadingArtist">Loading artist info...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>

    <div v-else-if="artist && !isEditing" class="artist-header">
      <img
        v-if="artist.artist_picture"
        :src="artist.artist_picture"
        :alt="`${artist.name} picture`"
        class="artist-pic"
      />
      <div v-else class="artist-pic-placeholder">No Pic</div>
      <div class="artist-info">
        <h1>{{ artist.name }}</h1>
        <div class="artist-meta">
          <span v-if="artist.location"
            ><i class="fas fa-map-marker-alt"></i> {{ artist.location }}</span
          >
          <a
            v-if="artist.website_url"
            :href="artist.website_url"
            target="_blank"
            rel="noopener noreferrer"
          >
            <i class="fas fa-link"></i> Website
          </a>
        </div>
        <p v-if="artist.bio" class="artist-bio">{{ artist.bio }}</p>
        <p v-else class="artist-bio">No biography available.</p>

        <div class="artist-actions">
          <button
            v-if="isOwner"
            @click="
              isEditing = true;
              editError = null;
            "
            class="edit-button action-button"
          >
            Edit Artist Profile
          </button>

          <!-- Follow/Unfollow Button -->
          <button
            v-if="
              authStore.isLoggedIn && !isOwner && !isViewingOwnArtistProfile
            "
            @click="handleFollowToggle"
            :disabled="isLoadingFollowStatus || isLoadingFollowAction"
            class="action-button follow-button"
            :class="{ 'is-following': isFollowing }"
          >
            {{ followButtonText }}
          </button>
          <p v-else-if="!authStore.isLoggedIn && !isOwner" class="info-text">
            <RouterLink
              :to="{ name: 'login', query: { redirect: route.fullPath } }"
              >Login</RouterLink
            >
            to follow.
          </p>
          <!-- End Follow/Unfollow Button -->

          <button
            v-if="authStore.isLoggedIn && !isViewingOwnArtistProfile"
            @click="startChatWithArtist"
            class="action-button send-message-button"
          >
            Send Message
          </button>
          <p
            v-else-if="isViewingOwnArtistProfile"
            class="info-text self-profile-text"
          >
            This is your artist profile.
          </p>
          <p
            v-else-if="!authStore.isLoggedIn && !isViewingOwnArtistProfile"
            class="info-text"
          >
            <RouterLink
              :to="{ name: 'login', query: { redirect: route.fullPath } }"
              >Login</RouterLink
            >
            to send a message.
          </p>
        </div>
      </div>
    </div>

    <div v-else-if="artist && isEditing && isOwner">
      <h2>Edit Artist Profile</h2>
      <p v-if="editError" class="error-message">{{ editError }}</p>
      <ArtistEditForm
        :artist-id="props.id"
        :initial-data="artist"
        @artist-updated="onArtistUpdate"
        @cancel-edit="
          isEditing = false;
          editError = null;
        "
        @update-error="handleUpdateError"
      />
    </div>

    <div class="artist-releases">
      <h2>Releases by {{ artist?.name || "this artist" }}</h2>
      <div v-if="isLoadingReleases">Loading releases...</div>
      <div v-else-if="!releases || releases.length === 0">
        No releases found for this artist.
      </div>
      <div v-else class="releases-grid">
        <RouterLink
          v-for="releaseItem in releases"
          :key="releaseItem.id"
          :to="{ name: 'release-detail', params: { id: releaseItem.id } }"
          class="release-card"
        >
          <img
            v-if="releaseItem.cover_art"
            :src="releaseItem.cover_art"
            :alt="`${releaseItem.title} cover art`"
            class="cover-art"
          />
          <div v-else class="cover-art-placeholder">No Cover</div>
          <h3>{{ releaseItem.title }}</h3>
          <span class="release-type">{{
            releaseItem.release_type_display || releaseItem.release_type
          }}</span>
        </RouterLink>
      </div>
    </div>

    <button @click="router.back()" class="back-button">Go Back</button>

    <ChooseSenderIdentityModal
      :is-visible="showIdentityModal"
      @identity-chosen="proceedWithChatNavigation"
      @close="showIdentityModal = false"
    />
  </div>
</template>

<style scoped>
/* Styles remain the same as previous ArtistDetailView.vue */
.artist-detail-page {
  max-width: 900px;
  margin: 1rem auto;
}
.artist-header {
  display: flex;
  gap: 2rem;
  margin-bottom: 2.5rem;
  align-items: center;
}
.artist-pic,
.artist-pic-placeholder {
  flex-shrink: 0;
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  border: 2px solid var(--color-border);
}
.artist-info {
  flex-grow: 1;
}
.artist-info h1 {
  margin-top: 0;
  margin-bottom: 0.5rem;
}
.artist-meta {
  margin-bottom: 1rem;
  font-size: 0.9em;
  color: var(--color-text);
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap; /* Allow meta items to wrap */
}
.artist-meta a {
  color: var(--color-link);
  text-decoration: none;
}
.artist-meta a:hover {
  text-decoration: underline;
}
.artist-bio {
  line-height: 1.6;
  margin-bottom: 1rem;
}
.artist-actions {
  margin-top: 1rem;
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap; /* Allow buttons to wrap */
}
.action-button {
  /* General style for action buttons */
  padding: 0.6em 1.2em;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.95em;
  border: 1px solid transparent;
}
.edit-button {
  background-color: var(--color-background-mute);
  border-color: var(--color-border);
  color: var(--color-text);
}
.edit-button:hover {
  border-color: var(--color-border-hover);
}

.follow-button {
  background-color: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}
.follow-button.is-following {
  background-color: var(--color-background-soft);
  color: var(--color-accent);
  border-color: var(--color-accent);
}
.follow-button:hover:not(:disabled) {
  opacity: 0.85;
}
.follow-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.send-message-button {
  background-color: #5cb85c; /* Example: Green for message */
  color: white;
  border-color: #4cae4c;
}
.send-message-button:hover {
  background-color: #4cae4c;
}

.info-text {
  font-size: 0.9em;
  color: var(--color-text-light);
}
.self-profile-text {
  font-style: italic;
}

.artist-releases {
  margin-top: 3rem;
}
.artist-releases h2 {
  margin-bottom: 1.5rem;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 0.5rem;
}
.releases-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 1.5rem;
}
.release-card {
  border: 1px solid var(--color-border);
  padding: 0.8rem;
  border-radius: 8px;
  text-align: center;
  background-color: var(--color-background-soft);
  transition: transform 0.2s ease-in-out;
  display: block;
  color: inherit;
  text-decoration: none;
}
.release-card:hover {
  transform: translateY(-4px);
}
.cover-art,
.cover-art-placeholder {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  margin-bottom: 0.5rem;
  background-color: var(--color-background-mute);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text);
  font-size: 0.9em;
  border-radius: 4px;
}
.release-card h3 {
  font-size: 1em;
  margin-bottom: 0.2rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.release-type {
  font-size: 0.75em;
  color: var(--color-text);
  background-color: var(--color-background-mute);
  padding: 0.1em 0.4em;
  border-radius: 4px;
}
.error-message {
  color: red;
  background-color: #ffe0e0;
  border: 1px solid red;
  padding: 0.5em;
  border-radius: 4px;
  margin-bottom: 1em;
}
.back-button {
  margin-top: 2rem;
  padding: 0.6em 1.2em;
  border-radius: 5px;
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.back-button:hover {
  border-color: var(--color-border-hover);
}
</style>
