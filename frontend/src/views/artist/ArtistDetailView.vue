<script setup lang="ts">
import { ref, onMounted, watch, computed } from "vue";
import { RouterLink, useRouter } from "vue-router";
import axios from "axios";
import { useAuthStore } from "@/stores/auth";
import ArtistEditForm from "@/components/artist/ArtistEditForm.vue"; // Updated import path
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
const chatStore = useChatStore();
const router = useRouter();
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

const isMyArtistProfile = computed(() => {
  return (
    authStore.isLoggedIn && authStore.artistProfileId === parseInt(props.id, 10)
  );
});

const fetchArtistDetail = async (artistId: string) => {
  isLoadingArtist.value = true;
  error.value = null;
  artist.value = null;
  try {
    const response = await axios.get<ArtistDetail>(`/artists/${artistId}/`);
    artist.value = response.data;
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
        // This case handles when the target artist's USER account DMed THIS artist profile,
        // and I am now trying to reply as USER to this artist profile.
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
  showIdentityModal.value = false; // Close modal after navigation
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
  if (authStore.artistProfileId === artist.value.id) {
    alert(
      "You cannot send a message to your own artist profile using this button."
    );
    return;
  }

  if (authStore.hasArtistProfile) {
    showIdentityModal.value = true;
  } else {
    proceedWithChatNavigation("USER");
  }
};

// No need for handleIdentityChosen here as it's encapsulated in the modal component.
// The modal will emit 'identity-chosen' which `proceedWithChatNavigation` handles.

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
            class="edit-button"
          >
            Edit Artist Profile
          </button>

          <button
            v-if="
              authStore.isLoggedIn && artist.user_id !== authStore.authUser?.id
            "
            @click="startChatWithArtist"
            class="send-message-button"
          >
            Send Message
          </button>
          <p
            v-else-if="
              authStore.isLoggedIn && artist.user_id === authStore.authUser?.id
            "
            class="info-text self-profile-text"
          >
            This is your artist profile.
          </p>
          <p v-else class="info-text">
            <RouterLink
              :to="{
                name: 'login',
                query: { redirect: router.currentRoute.value.fullPath },
              }"
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
}
.edit-button,
.send-message-button {
  padding: 0.6em 1.2em;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.95em;
}
.edit-button {
  background-color: var(--color-background-mute);
  border: 1px solid var(--color-border);
  color: var(--color-text);
}
.edit-button:hover {
  border-color: var(--color-border-hover);
}
.send-message-button {
  background-color: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
}
.send-message-button:hover {
  background-color: var(--color-accent-hover);
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
