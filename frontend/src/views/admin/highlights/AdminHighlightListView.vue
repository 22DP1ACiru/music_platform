<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import axios from "axios";
import { RouterLink } from "vue-router";
import type { AdminHighlightInfo } from "@/types";

interface PaginatedHighlightsResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: AdminHighlightInfo[];
}

const highlights = ref<AdminHighlightInfo[]>([]);
const isLoading = ref(true);
const error = ref<string | null>(null);

async function fetchAdminHighlights() {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await axios.get<PaginatedHighlightsResponse>(
      "/highlights/admin-list/"
    );
    highlights.value = response.data.results;
  } catch (err) {
    console.error("AdminHighlightListView: Failed to fetch highlights:", err);
    error.value = "Could not load highlights data.";
  } finally {
    isLoading.value = false;
  }
}

async function deleteHighlight(highlightId: number) {
  if (
    !confirm(
      "Are you sure you want to delete this highlight? This cannot be undone."
    )
  ) {
    return;
  }
  try {
    await axios.delete(`/highlights/${highlightId}/`);
    highlights.value = highlights.value.filter((h) => h.id !== highlightId);
    alert("Highlight deleted successfully.");
  } catch (err) {
    console.error(
      `AdminHighlightListView: Failed to delete highlight ${highlightId}:`,
      err
    );
    alert("Failed to delete highlight. Please try again.");
  }
}

onMounted(fetchAdminHighlights);

const formatDisplayDateTime = (dateTimeString: string | null | undefined) => {
  if (!dateTimeString) return "N/A";
  try {
    return new Date(dateTimeString).toLocaleString();
  } catch (e) {
    return "Invalid Date";
  }
};
</script>

<template>
  <div class="admin-highlight-list-view">
    <div class="header-actions">
      <h2>Manage Highlights</h2>
      <RouterLink
        :to="{ name: 'admin-highlight-create' }"
        class="action-button create-new-btn"
      >
        + Create New Highlight
      </RouterLink>
    </div>

    <div v-if="isLoading" class="loading-message">Loading highlights...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="highlights.length === 0" class="empty-state">
      No highlights found.
      <RouterLink :to="{ name: 'admin-highlight-create' }"
        >Create one now?</RouterLink
      >
    </div>

    <table v-else class="highlights-table">
      <thead>
        <tr>
          <th>Order</th>
          <th>Highlight Title</th>
          <th>Release (Artist - Title)</th>
          <th>Active</th>
          <th>Start Date</th>
          <th>End Date</th>
          <th>Created By</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="highlight in highlights" :key="highlight.id">
          <td>{{ highlight.order }}</td>
          <td>{{ highlight.effective_title }}</td>
          <td class="release-info-cell">
            <RouterLink
              v-if="highlight.release"
              :to="{
                name: 'release-detail',
                params: { id: highlight.release },
              }"
            >
              {{ highlight.release_artist_name || "N/A" }} -
              {{ highlight.release_title || "(No Release Title)" }}
            </RouterLink>
            <span v-else class="no-release-text">(Generic Highlight)</span>
          </td>
          <td>{{ highlight.is_active ? "Yes" : "No" }}</td>
          <td>{{ formatDisplayDateTime(highlight.display_start_datetime) }}</td>
          <td>{{ formatDisplayDateTime(highlight.display_end_datetime) }}</td>
          <td>{{ highlight.created_by || "N/A" }}</td>
          <td class="actions-cell">
            <RouterLink
              :to="{
                name: 'admin-highlight-edit',
                params: { highlightId: highlight.id },
              }"
              class="action-button edit-btn"
            >
              Edit
            </RouterLink>
            <button
              @click="deleteHighlight(highlight.id)"
              class="action-button delete-btn"
            >
              Delete
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.admin-highlight-list-view {
  padding: 1rem;
}
.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.header-actions h2 {
  margin: 0;
  color: var(--color-heading);
}
.create-new-btn {
  background-color: var(--color-accent);
  color: white;
  padding: 0.6em 1.2em;
  border-radius: 5px;
  text-decoration: none;
  font-size: 0.95em;
}
.create-new-btn:hover {
  background-color: var(--color-accent-hover);
}

.loading-message,
.empty-state {
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
}

.highlights-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
  background-color: var(--color-background);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}
.highlights-table th,
.highlights-table td {
  border: 1px solid var(--color-border);
  padding: 0.75rem 1rem;
  text-align: left;
  vertical-align: middle;
}
.highlights-table th {
  background-color: var(--color-background-soft);
  font-weight: 600;
  color: var(--color-heading);
}
.highlights-table tbody tr:nth-child(even) {
  background-color: var(--color-background-mute);
}
.highlights-table tbody tr:hover {
  background-color: var(--color-border-hover);
}

.release-info-cell .no-release-text {
  font-style: italic;
  color: var(--color-text-light);
}

.actions-cell {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  min-width: 130px; /* Give enough space for buttons */
}
.action-button {
  padding: 0.4em 0.8em; /* Slightly increased padding for better clickability */
  font-size: 0.9em;
  border-radius: 4px;
  text-decoration: none;
  cursor: pointer;
  border: 1px solid transparent;
  transition: background-color 0.2s ease, border-color 0.2s ease; /* Smooth transitions */
  display: inline-block; /* Ensures proper spacing and alignment */
  text-align: center;
  line-height: 1.2; /* Better vertical centering of text */
}
.edit-btn {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-color: var(--color-border);
}
.edit-btn:hover {
  border-color: var(--color-accent);
  background-color: var(
    --color-accent-soft,
    #e6f7ff
  ); /* Lighter accent for hover */
  color: var(--color-accent);
}
.delete-btn {
  background-color: var(--vt-c-red-soft);
  color: var(--vt-c-red-dark);
  border-color: var(--vt-c-red-dark);
}
.delete-btn:hover {
  background-color: var(--vt-c-red);
  border-color: var(--vt-c-red-dark);
  color: white;
}
</style>
