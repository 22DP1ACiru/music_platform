<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import axios from "axios";
import type { ReleaseSummary } from "@/types";

interface PaginatedReleasesResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: ReleaseSummary[];
}

const props = defineProps({
  isVisible: {
    type: Boolean,
    required: true,
  },
});

const emit = defineEmits(["close", "release-selected"]);

const releases = ref<ReleaseSummary[]>([]);
const currentPage = ref(1);
const totalPages = ref(1);
const totalReleases = ref(0);
const searchQuery = ref("");
const isLoading = ref(false);
const error = ref<string | null>(null);
const itemsPerPage = 5;

async function fetchReleases(page: number = 1, query: string = "") {
  isLoading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams();
    params.append("page", page.toString());
    params.append("limit", itemsPerPage.toString());
    if (query.trim()) {
      params.append("search", query.trim());
    }

    const response = await axios.get<PaginatedReleasesResponse>(
      `/releases/?${params.toString()}`
    );
    releases.value = response.data.results;
    totalReleases.value = response.data.count;
    totalPages.value = Math.ceil(response.data.count / itemsPerPage);
    currentPage.value = page;
  } catch (err) {
    console.error("ReleaseSelectorModal: Failed to fetch releases:", err);
    error.value = "Could not load releases.";
    releases.value = [];
    totalPages.value = 1;
    totalReleases.value = 0;
  } finally {
    isLoading.value = false;
  }
}

function selectRelease(release: ReleaseSummary) {
  emit("release-selected", release);
  emit("close");
}

function closeModal() {
  emit("close");
}

function handleSearch() {
  fetchReleases(1, searchQuery.value);
}

function changePage(newPage: number) {
  if (newPage >= 1 && newPage <= totalPages.value) {
    fetchReleases(newPage, searchQuery.value);
  }
}

watch(
  () => props.isVisible,
  (newVal) => {
    if (newVal) {
      searchQuery.value = ""; // Reset search on open
      fetchReleases(); // Fetch initial list
    } else {
      releases.value = []; // Clear list on close to save memory
    }
  }
);

onMounted(() => {
  if (props.isVisible) {
    fetchReleases();
  }
});
</script>

<template>
  <div v-if="isVisible" class="modal-overlay" @click.self="closeModal">
    <div class="modal-content">
      <div class="modal-header">
        <h3>Select a Release</h3>
        <button @click="closeModal" class="close-btn">&times;</button>
      </div>
      <div class="modal-body">
        <form @submit.prevent="handleSearch" class="search-form">
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search releases by title or artist..."
          />
          <button type="submit" :disabled="isLoading">Search</button>
        </form>

        <div v-if="isLoading" class="loading-message">Loading...</div>
        <div v-else-if="error" class="error-message">{{ error }}</div>
        <div v-else-if="releases.length === 0" class="empty-message">
          No releases found.
        </div>

        <ul v-else class="release-list">
          <li
            v-for="release in releases"
            :key="release.id"
            @click="selectRelease(release)"
            class="release-item"
          >
            <img
              v-if="release.cover_art"
              :src="release.cover_art"
              :alt="release.title"
              class="item-cover"
            />
            <div v-else class="item-cover placeholder">🎧</div>
            <div class="item-info">
              <span class="item-title">{{ release.title }}</span>
              <span class="item-artist"
                >by {{ release.artist?.name || "Unknown Artist" }}</span
              >
            </div>
          </li>
        </ul>

        <div v-if="totalPages > 1" class="pagination-controls">
          <button
            @click="changePage(currentPage - 1)"
            :disabled="currentPage <= 1 || isLoading"
          >
            Prev
          </button>
          <span>Page {{ currentPage }} of {{ totalPages }}</span>
          <button
            @click="changePage(currentPage + 1)"
            :disabled="currentPage >= totalPages || isLoading"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1100; /* Higher than other modals if any */
}
.modal-content {
  background-color: var(--color-background-soft);
  padding: 0; /* Remove padding here, header/body will handle */
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35);
  width: 90%;
  max-width: 600px;
  display: flex;
  flex-direction: column;
  max-height: 80vh;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--color-border);
}
.modal-header h3 {
  margin: 0;
  font-size: 1.4em;
  color: var(--color-heading);
}
.close-btn {
  background: none;
  border: none;
  font-size: 2rem;
  color: var(--color-text-light);
  cursor: pointer;
  padding: 0;
  line-height: 1;
}
.modal-body {
  padding: 1.5rem;
  overflow-y: auto; /* Allows scrolling for list and pagination */
}

.search-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.search-form input {
  flex-grow: 1;
  padding: 0.6rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
}
.search-form button {
  padding: 0.6rem 1rem;
  background-color: var(--color-accent);
  color: white;
  border: none;
  border-radius: 4px;
}

.release-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.release-item {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-bottom: 1px solid var(--color-border-hover);
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.15s ease;
}
.release-item:hover {
  background-color: var(--color-background-mute);
}
.release-item:last-child {
  border-bottom: none;
}
.item-cover {
  width: 50px;
  height: 50px;
  object-fit: cover;
  border-radius: 3px;
  margin-right: 1rem;
  background-color: var(--color-background-mute);
  flex-shrink: 0;
}
.item-cover.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}
.item-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.item-title {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.item-artist {
  font-size: 0.85em;
  color: var(--color-text-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
}
.pagination-controls button {
  padding: 0.4rem 0.8rem;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-soft);
  border-radius: 4px;
}
.pagination-controls button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.loading-message,
.empty-message,
.error-message {
  text-align: center;
  padding: 1rem;
  font-style: italic;
  color: var(--color-text-light);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red);
}
</style>
