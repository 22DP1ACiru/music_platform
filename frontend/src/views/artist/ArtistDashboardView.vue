<script setup lang="ts">
import { onMounted, computed, ref, watch } from "vue";
import { useStatsStore } from "@/stores/stats";
import { useAuthStore } from "@/stores/auth";
import { useRouter, RouterLink } from "vue-router";

const statsStore = useStatsStore();
const authStore = useAuthStore();
const router = useRouter();

const selectedPeriod = ref("all_time"); // Default period

const stats = computed(() => statsStore.artistDashboardStats);
const isLoading = computed(() => statsStore.isLoadingArtistStats);
const error = computed(() => statsStore.errorArtistStats);

const fetchStatsForPeriod = () => {
  if (authStore.hasArtistProfile) {
    statsStore.fetchArtistDashboardStats(selectedPeriod.value);
  }
};

onMounted(() => {
  if (!authStore.isLoggedIn || !authStore.hasArtistProfile) {
    // Redirect if not an artist or not logged in
    // Consider showing a message or redirecting from router guard as well
    alert("You need to be an artist to view this page.");
    router.push({ name: "profile" }); // Or home
  } else {
    fetchStatsForPeriod();
  }
});

watch(selectedPeriod, () => {
  fetchStatsForPeriod();
});

const formatNumber = (num: number | undefined) => {
  return num !== undefined ? num.toLocaleString() : "0";
};

const formatCurrency = (value: string | undefined) => {
  if (value === undefined) return "$0.00";
  const num = parseFloat(value);
  return `$${num.toFixed(2)}`; // Assuming USD for now
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
  <div class="artist-dashboard-view">
    <h2>Your Artist Dashboard</h2>

    <div class="period-selector form-group">
      <label for="stats-period">Select Period:</label>
      <select id="stats-period" v-model="selectedPeriod">
        <option value="all_time">All Time</option>
        <option value="30days">Last 30 Days</option>
        <option value="7days">Last 7 Days</option>
      </select>
    </div>

    <div v-if="isLoading" class="loading-message">Loading statistics...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!stats" class="empty-message">
      No statistics available yet.
    </div>

    <div v-else class="stats-content">
      <!-- Summary Section -->
      <section class="stats-section summary-section">
        <h3>Summary</h3>
        <div class="summary-grid">
          <div class="summary-card">
            <h4>Total Release Listens</h4>
            <p>{{ formatNumber(stats.summary.total_release_listens) }}</p>
          </div>
          <div class="summary-card">
            <h4>Total Track Listens</h4>
            <p>{{ formatNumber(stats.summary.total_track_listens) }}</p>
          </div>
          <div class="summary-card">
            <h4>Total Sales Count</h4>
            <p>{{ formatNumber(stats.summary.total_sales_count) }}</p>
          </div>
          <div class="summary-card">
            <h4>Total Sales Revenue (USD)</h4>
            <p>{{ formatCurrency(stats.summary.total_sales_value_usd) }}</p>
          </div>
          <div class="summary-card">
            <h4>Current Followers</h4>
            <p>{{ formatNumber(stats.summary.current_follower_count) }}</p>
          </div>
        </div>
      </section>

      <!-- Top Releases Section -->
      <section class="stats-section top-items-section">
        <h3>Top Releases (by listens)</h3>
        <div
          v-if="!stats.top_releases || stats.top_releases.length === 0"
          class="empty-subsection"
        >
          No release data for this period.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="release in stats.top_releases"
            :key="`release-${release.id}`"
            class="top-list-item"
          >
            <RouterLink
              :to="{ name: 'release-detail', params: { id: release.id } }"
            >
              <img
                :src="release.cover_art || '/placeholder-cover.png'"
                :alt="release.title"
                class="item-cover-art-small"
              />
              <div class="item-info">
                <span class="item-title">{{ release.title }}</span>
                <span class="item-detail">{{
                  release.release_type_display
                }}</span>
              </div>
              <span class="item-stat"
                >{{ formatNumber(release.listen_count) }} listens</span
              >
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- Top Tracks Section -->
      <section class="stats-section top-items-section">
        <h3>Top Tracks (by listens)</h3>
        <div
          v-if="!stats.top_tracks || stats.top_tracks.length === 0"
          class="empty-subsection"
        >
          No track data for this period.
        </div>
        <ul v-else class="top-list">
          <li
            v-for="track in stats.top_tracks"
            :key="`track-${track.id}`"
            class="top-list-item"
          >
            <!-- Link to release detail, then track on page if possible -->
            <RouterLink
              :to="{ name: 'release-detail', params: { id: track.release_id } }"
              v-if="track.release_id"
            >
              <div class="item-info">
                <span class="item-title">{{ track.title }}</span>
                <span class="item-detail">
                  from {{ track.release_title || "Unknown Release" }}
                </span>
                <span class="item-detail"
                  >Duration:
                  {{ formatDuration(track.duration_in_seconds) }}</span
                >
              </div>
              <span class="item-stat"
                >{{ formatNumber(track.listen_count) }} listens</span
              >
            </RouterLink>
            <div v-else class="item-info no-link">
              <!-- Fallback if no release_id -->
              <span class="item-title">{{ track.title }}</span>
              <span class="item-detail"
                >Duration: {{ formatDuration(track.duration_in_seconds) }}</span
              >
              <span class="item-stat"
                >{{ formatNumber(track.listen_count) }} listens</span
              >
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<style scoped>
.artist-dashboard-view {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1.5rem;
}
.artist-dashboard-view h2 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--color-heading);
}

.period-selector {
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.period-selector label {
  font-weight: 500;
}
.period-selector select {
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

.stats-content {
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1rem;
}
.summary-card {
  background-color: var(--color-background-mute);
  padding: 1rem;
  border-radius: 6px;
  text-align: center;
}
.summary-card h4 {
  margin-top: 0;
  margin-bottom: 0.5rem;
  font-size: 1em;
  color: var(--color-text);
}
.summary-card p {
  font-size: 1.5em;
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
.top-list-item .no-link {
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
.top-list-item:last-child a {
  border-bottom: none;
}

.item-cover-art-small {
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-border);
  flex-shrink: 0;
}
.item-info {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}
.item-title {
  font-weight: 500;
  color: var(--color-heading);
}
.item-detail {
  font-size: 0.85em;
  color: var(--color-text-light);
}
.item-stat {
  font-weight: bold;
  color: var(--color-accent);
  margin-left: auto;
  font-size: 0.9em;
  white-space: nowrap;
}
</style>
