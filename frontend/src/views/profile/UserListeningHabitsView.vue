<script setup lang="ts">
import { onMounted, computed, ref, watch } from "vue";
import { useUserStatsStore } from "@/stores/userStats";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink } from "vue-router";

const userStatsStore = useUserStatsStore();
const authStore = useAuthStore();
const router = useRouter();

const selectedPeriod = ref("all_time");
const selectedLimit = ref(5);

const habits = computed(() => userStatsStore.listeningHabits);
const isLoading = computed(() => userStatsStore.isLoading);
const error = computed(() => userStatsStore.error);

const VITE_API_BASE_URL_FOR_IMAGES =
  import.meta.env.VITE_API_URL?.replace("/api", "") || "";

const fetchHabits = () => {
  if (authStore.isLoggedIn) {
    userStatsStore.fetchMyListeningHabits(
      selectedPeriod.value,
      selectedLimit.value
    );
  }
};

onMounted(() => {
  if (!authStore.isLoggedIn) {
    router.push({
      name: "login",
      query: { redirect: "/profile/listening-habits" },
    });
  } else {
    fetchHabits();
  }
});

watch([selectedPeriod, selectedLimit], () => {
  fetchHabits();
});

const formatNumber = (num: number | undefined | null) => {
  return num !== undefined && num !== null ? num.toLocaleString() : "0";
};

const getFullImageUrl = (
  imagePath: string | null | undefined
): string | null => {
  // If imagePath is null, undefined, or an empty string, return null to trigger placeholder
  if (!imagePath) {
    return null;
  }
  return `${VITE_API_BASE_URL_FOR_IMAGES}/media/${imagePath}`;
};

const formatDuration = (totalSeconds: number | null | undefined): string => {
  if (
    totalSeconds === null ||
    totalSeconds === undefined ||
    totalSeconds < 0 ||
    !isFinite(totalSeconds)
  ) {
    return "--:--";
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
};
</script>

<template>
  <div class="user-listening-habits-view">
    <h2>Your Listening Habits</h2>

    <div class="controls-bar">
      <div class="form-group period-selector">
        <label for="habits-period">Select Period:</label>
        <select id="habits-period" v-model="selectedPeriod">
          <option value="all_time">All Time</option>
          <option value="30days">Last 30 Days</option>
          <option value="7days">Last 7 Days</option>
        </select>
      </div>
      <div class="form-group limit-selector">
        <label for="habits-limit">Show Top:</label>
        <select id="habits-limit" v-model.number="selectedLimit">
          <option value="3">3</option>
          <option value="5">5</option>
          <option value="10">10</option>
        </select>
      </div>
    </div>

    <div v-if="isLoading" class="loading-message">Loading your habits...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div
      v-else-if="!habits || habits.total_listen_events_count === 0"
      class="empty-message"
    >
      No listening data available for this period. Start listening to some
      music!
    </div>

    <div v-else class="habits-content">
      <section class="stats-section">
        <h3>Overall Activity</h3>
        <div class="summary-card">
          <h4>Total Significant Listens</h4>
          <p>{{ formatNumber(habits.total_listen_events_count) }}</p>
        </div>
      </section>

      <!-- Top Tracks Section -->
      <section class="stats-section">
        <h3>Your Top {{ selectedLimit }} Tracks</h3>
        <div
          v-if="
            !habits.top_listened_tracks ||
            habits.top_listened_tracks.length === 0
          "
          class="empty-subsection"
        >
          No track data for this period.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="track in habits.top_listened_tracks"
            :key="`track-${track.id}`"
            class="top-list-item"
          >
            <RouterLink
              :to="{ name: 'release-detail', params: { id: track.release_id } }"
              v-if="track.release_id"
            >
              <img
                v-if="getFullImageUrl(track.cover_art)"
                :src="getFullImageUrl(track.cover_art)!"
                :alt="track.title"
                class="item-cover-art-small"
              />
              <div v-else class="item-cover-art-small placeholder">🎧</div>
              <div class="item-info">
                <span class="item-title">{{ track.title }}</span>
                <span class="item-detail"
                  >by {{ track.artist_name || "Unknown Artist" }}</span
                >
                <span class="item-detail"
                  >from {{ track.release_title || "Unknown Release" }}</span
                >
              </div>
              <span class="item-stat"
                >{{ formatNumber(track.user_listen_count) }} listens</span
              >
            </RouterLink>
            <div v-else class="item-info no-link">
              <div class="item-cover-art-small placeholder">🎧</div>
              <div class="item-info">
                <span class="item-title">{{ track.title }}</span>
                <span class="item-detail"
                  >by {{ track.artist_name || "Unknown Artist" }}</span
                >
              </div>
              <span class="item-stat"
                >{{ formatNumber(track.user_listen_count) }} listens</span
              >
            </div>
          </li>
        </ul>
      </section>

      <!-- Top Artists Section -->
      <section class="stats-section">
        <h3>Your Top {{ selectedLimit }} Artists</h3>
        <div
          v-if="
            !habits.top_listened_artists ||
            habits.top_listened_artists.length === 0
          "
          class="empty-subsection"
        >
          No artist data for this period.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="artist in habits.top_listened_artists"
            :key="`artist-${artist.id}`"
            class="top-list-item"
          >
            <RouterLink
              :to="{ name: 'artist-detail', params: { id: artist.id } }"
            >
              <img
                v-if="getFullImageUrl(artist.artist_picture)"
                :src="getFullImageUrl(artist.artist_picture)!"
                :alt="artist.name"
                class="item-cover-art-small artist-pic"
              />
              <div v-else class="item-cover-art-small artist-pic placeholder">
                👤
              </div>
              <div class="item-info">
                <span class="item-title">{{ artist.name }}</span>
              </div>
              <span class="item-stat"
                >{{
                  formatNumber(artist.user_listen_count_for_artist)
                }}
                listens</span
              >
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Top Genres Section -->
      <section class="stats-section">
        <h3>Your Top {{ selectedLimit }} Genres</h3>
        <div
          v-if="
            !habits.top_listened_genres ||
            habits.top_listened_genres.length === 0
          "
          class="empty-subsection"
        >
          Keep listening to discover your top genres! (Or assign genres to
          tracks)
        </div>
        <ul v-else class="top-list genre-list">
          <li
            v-for="genre in habits.top_listened_genres"
            :key="`genre-${genre.id}`"
            class="top-list-item genre-item"
          >
            <div class="item-info">
              <span class="item-title genre-name">{{ genre.name }}</span>
            </div>
            <span class="item-stat"
              >{{
                formatNumber(genre.user_listen_count_for_genre)
              }}
              listens</span
            >
          </li>
        </ul>
      </section>
    </div>
    <RouterLink :to="{ name: 'profile' }" class="back-button"
      >Back to Profile</RouterLink
    >
  </div>
</template>

<style scoped>
.user-listening-habits-view {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1.5rem;
}
.user-listening-habits-view h2 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--color-heading);
}
.controls-bar {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  align-items: center;
  flex-wrap: wrap;
}
.form-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.form-group label {
  font-weight: 500;
  color: var(--color-text);
}
.form-group select {
  padding: 0.5em 0.8em;
  border-radius: 4px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background);
  color: var(--color-text);
}

.loading-message,
.empty-message,
.empty-subsection {
  text-align: center;
  padding: 2rem;
  font-style: italic;
  color: var(--color-text-light);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  text-align: center;
}

.habits-content {
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
}

.stats-section {
  background-color: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}
.stats-section h3 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border-hover);
  padding-bottom: 0.75rem;
}

.summary-card {
  background-color: var(--color-background-mute);
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  margin-bottom: 1rem;
}
.summary-card h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1em;
  color: var(--color-text);
}
.summary-card p {
  font-size: 1.8em;
  font-weight: bold;
  color: var(--color-accent);
  margin: 0;
}

.top-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.top-list-item a,
.top-list-item .no-link,
.top-list-item.genre-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--color-border-hover);
  text-decoration: none;
  color: var(--color-text);
  transition: background-color 0.2s ease;
}
.top-list-item a:hover {
  background-color: var(--color-background-mute);
}
.top-list-item:last-child a,
.top-list-item.genre-item:last-child {
  border-bottom: none;
}

.item-cover-art-small {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(
    --color-border
  ); /* Fallback background for placeholder */
  flex-shrink: 0;
  display: flex; /* For placeholder icon centering */
  align-items: center; /* For placeholder icon centering */
  justify-content: center; /* For placeholder icon centering */
}
.item-cover-art-small.artist-pic {
  border-radius: 50%;
}
.item-cover-art-small.placeholder {
  font-size: 1.5em; /* Size of the icon inside placeholder */
  color: var(--color-text-light);
}

.item-info {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.item-title {
  font-weight: 500;
  color: var(--color-heading);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.genre-list .item-title {
  font-size: 1.1em;
}
.item-detail {
  font-size: 0.85em;
  color: var(--color-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-stat {
  font-weight: bold;
  color: var(--color-accent);
  margin-left: auto;
  font-size: 0.9em;
  white-space: nowrap;
  padding-left: 1rem;
}
.back-button {
  display: inline-block;
  margin-top: 2rem;
  padding: 0.6em 1.2em;
  text-decoration: none;
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  transition: background-color 0.2s ease;
}
.back-button:hover {
  background-color: var(--color-border-hover);
}
</style>
