<script setup lang="ts">
import { onMounted, computed, ref, watch } from "vue";
import { useAdminStatsStore } from "@/stores/adminStats";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink } from "vue-router";

const adminStatsStore = useAdminStatsStore();
const authStore = useAuthStore();
const router = useRouter();

const selectedPeriod = ref("all_time");
const selectedLimit = ref(5);

const overview = computed(() => adminStatsStore.platformOverview);
const isLoading = computed(() => adminStatsStore.isLoading);
const error = computed(() => adminStatsStore.error);

const VITE_API_BASE_URL_FOR_IMAGES =
  import.meta.env.VITE_API_URL?.replace("/api", "") || "";

const fetchStats = () => {
  if (authStore.isStaff) {
    adminStatsStore.fetchPlatformOverview(
      selectedPeriod.value,
      selectedLimit.value
    );
  }
};

onMounted(() => {
  if (!authStore.isStaff) {
    alert("Access denied. You must be an administrator.");
    router.push({ name: "home" });
  } else {
    fetchStats();
  }
});

watch([selectedPeriod, selectedLimit], () => {
  fetchStats();
});

const formatNumber = (num: number | undefined) => {
  return num !== undefined ? num.toLocaleString() : "0";
};

const formatCurrency = (value: string | undefined) => {
  if (value === undefined) return "$0.00";
  const num = parseFloat(value);
  return `$${num.toFixed(2)}`; // Assuming USD
};

const getFullImageUrl = (
  imagePath: string | null | undefined
): string | null => {
  if (!imagePath) {
    return null; // No path, no image
  }
  // Check if imagePath is already a full URL
  if (imagePath.startsWith("http://") || imagePath.startsWith("https://")) {
    return imagePath;
  }
  // Otherwise, prepend base media URL
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
  <div class="admin-platform-stats-view">
    <h3>Platform Overview Statistics</h3>

    <div class="controls-bar">
      <div class="form-group period-selector">
        <label for="admin-stats-period">Select Period:</label>
        <select id="admin-stats-period" v-model="selectedPeriod">
          <option value="all_time">All Time</option>
          <option value="30days">Last 30 Days</option>
          <option value="7days">Last 7 Days</option>
        </select>
      </div>
      <div class="form-group limit-selector">
        <label for="admin-stats-limit">Show Top:</label>
        <select id="admin-stats-limit" v-model.number="selectedLimit">
          <option value="3">3</option>
          <option value="5">5</option>
          <option value="10">10</option>
        </select>
      </div>
    </div>

    <div v-if="isLoading" class="loading-message">
      Loading platform statistics...
    </div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!overview" class="empty-message">
      No platform statistics available.
    </div>

    <div v-else class="stats-layout">
      <!-- Platform Summary Section -->
      <section class="stats-section summary-section">
        <h4>
          Platform Summary
          <span class="period-note"
            >(Totals for users, artists, releases, tracks are all-time. Listens
            & sales are for selected period)</span
          >
        </h4>
        <div class="summary-grid">
          <div class="summary-card">
            <h5>Registered Users</h5>
            <p>
              {{
                formatNumber(overview.platform_summary.total_registered_users)
              }}
            </p>
          </div>
          <div class="summary-card">
            <h5>Total Artists</h5>
            <p>{{ formatNumber(overview.platform_summary.total_artists) }}</p>
          </div>
          <div class="summary-card">
            <h5>Total Releases</h5>
            <p>{{ formatNumber(overview.platform_summary.total_releases) }}</p>
          </div>
          <div class="summary-card">
            <h5>Total Tracks</h5>
            <p>{{ formatNumber(overview.platform_summary.total_tracks) }}</p>
          </div>
          <div class="summary-card">
            <h5>Significant Listens</h5>
            <p>
              {{ formatNumber(overview.platform_summary.total_listen_events) }}
            </p>
          </div>
          <div class="summary-card">
            <h5>Items Sold</h5>
            <p>
              {{ formatNumber(overview.platform_summary.total_sales_count) }}
            </p>
          </div>
          <div class="summary-card">
            <h5>Sales Revenue (USD)</h5>
            <p>
              {{
                formatCurrency(overview.platform_summary.total_sales_value_usd)
              }}
            </p>
          </div>
        </div>
      </section>

      <!-- Most Popular Releases Section -->
      <section class="stats-section top-items-section">
        <h4>
          Most Popular Releases
          <span class="period-note"
            >(Top {{ selectedLimit }} by all-time listens)</span
          >
        </h4>
        <div
          v-if="
            !overview.most_popular_releases ||
            overview.most_popular_releases.length === 0
          "
          class="empty-subsection"
        >
          No popular release data.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="release in overview.most_popular_releases"
            :key="`pop-release-${release.id}`"
            class="top-list-item"
          >
            <RouterLink
              :to="{ name: 'release-detail', params: { id: release.id } }"
            >
              <img
                v-if="getFullImageUrl(release.cover_art)"
                :src="getFullImageUrl(release.cover_art)!"
                :alt="release.title"
                class="item-cover-art-small"
              />
              <div v-else class="item-cover-art-small placeholder">🎧</div>
              <div class="item-info">
                <span class="item-title">{{ release.title }}</span>
                <span class="item-detail"
                  >by {{ release.artist_name || "Unknown Artist" }}</span
                >
              </div>
              <span class="item-stat"
                >{{ formatNumber(release.listen_count) }} listens</span
              >
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Most Popular Tracks Section -->
      <section class="stats-section top-items-section">
        <h4>
          Most Popular Tracks
          <span class="period-note"
            >(Top {{ selectedLimit }} by all-time listens)</span
          >
        </h4>
        <div
          v-if="
            !overview.most_popular_tracks ||
            overview.most_popular_tracks.length === 0
          "
          class="empty-subsection"
        >
          No popular track data.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="track in overview.most_popular_tracks"
            :key="`pop-track-${track.id}`"
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
                  >from {{ track.release_title || "Unknown Release" }}</span
                >
              </div>
              <span class="item-stat"
                >{{ formatNumber(track.listen_count) }} listens</span
              >
            </RouterLink>
            <div v-else class="item-info no-link">
              <div class="item-cover-art-small placeholder">🎧</div>
              <div class="item-info">
                <span class="item-title">{{ track.title }}</span>
              </div>
              <span class="item-stat"
                >{{ formatNumber(track.listen_count) }} listens</span
              >
            </div>
          </li>
        </ul>
      </section>

      <!-- Most Popular Genres Section -->
      <section class="stats-section top-items-section">
        <h4>
          Most Popular Genres
          <span class="period-note"
            >(Top {{ selectedLimit }} by number of tracks)</span
          >
        </h4>
        <div
          v-if="
            !overview.most_popular_genres ||
            overview.most_popular_genres.length === 0
          "
          class="empty-subsection"
        >
          No popular genre data. (Ensure tracks have genres assigned)
        </div>
        <ul v-else class="top-list genre-list">
          <li
            v-for="genre in overview.most_popular_genres"
            :key="`pop-genre-${genre.id}`"
            class="top-list-item genre-item"
          >
            <div class="item-info">
              <span class="item-title genre-name">{{ genre.name }}</span>
            </div>
            <span
              class="item-stat"
              v-if="genre.num_tracks_in_genre !== undefined"
              >{{ formatNumber(genre.num_tracks_in_genre) }} tracks</span
            >
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.admin-platform-stats-view {
  padding: 1rem;
}
.admin-platform-stats-view h3 {
  /* Main section title */
  text-align: center;
  margin-bottom: 1.5rem;
  font-size: 1.5em;
  color: var(--color-heading);
}

.controls-bar {
  display: flex;
  justify-content: center;
  gap: 1.5rem;
  margin-bottom: 2rem;
  align-items: center;
  flex-wrap: wrap;
  padding: 0.5rem;
  background-color: var(--color-background-mute);
  border-radius: 6px;
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

.stats-layout {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.stats-section {
  background-color: var(--color-background-soft);
  padding: 1.5rem;
  border-radius: 8px;
  border: 1px solid var(--color-border);
}
.stats-section h4 {
  /* Titles within sections */
  margin-top: 0;
  margin-bottom: 1.5rem;
  font-size: 1.2em;
  color: var(--color-heading);
  border-bottom: 1px solid var(--color-border-hover);
  padding-bottom: 0.75rem;
}
.period-note {
  font-size: 0.8em;
  font-weight: normal;
  color: var(--color-text-light);
  margin-left: 0.5em;
}

.summary-section .summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
}
.summary-card {
  background-color: var(--color-background);
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
  border: 1px solid var(--color-border-hover);
}
.summary-card h5 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 0.95em;
  color: var(--color-text);
  font-weight: 500;
}
.summary-card p {
  font-size: 1.6em;
  font-weight: bold;
  color: var(--color-accent);
  margin: 0;
}

.top-items-section .top-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.top-list-item a,
.top-list-item .no-link,
.top-list-item.genre-item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.6rem;
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
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 3px;
  background-color: var(--color-border);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.item-cover-art-small.artist-pic {
  border-radius: 50%;
}
.item-cover-art-small.placeholder {
  font-size: 1.3em;
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
  font-size: 0.95em;
}
.genre-list .item-title {
  font-size: 1.05em;
}
.item-detail {
  font-size: 0.8em;
  color: var(--color-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-stat {
  font-weight: 500;
  color: var(--color-accent);
  margin-left: auto;
  font-size: 0.85em;
  white-space: nowrap;
  padding-left: 0.8rem;
}
</style>
