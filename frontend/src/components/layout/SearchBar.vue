<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

const searchQuery = ref("");
const router = useRouter();

const performSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({
      name: "search-results",
      query: { q: searchQuery.value.trim() },
    });
    // searchQuery.value = ""; // Optionally clear after search
  }
};
</script>

<template>
  <form @submit.prevent="performSearch" class="search-bar-form">
    <input
      type="search"
      v-model="searchQuery"
      placeholder="Search artists, releases..."
      aria-label="Search"
      class="search-input"
    />
    <button type="submit" class="search-button">Search</button>
  </form>
</template>

<style scoped>
.search-bar-form {
  display: flex;
  align-items: center;
  gap: 0.5rem; /* Space between input and button */
}

.search-input {
  padding: 0.5em 0.8em;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 0.9em;
  background-color: var(--color-background); /* Ensure consistent bg */
  color: var(--color-text); /* Ensure consistent text color */
  min-width: 200px; /* Give it some default width */
}

.search-input:focus {
  border-color: var(--color-accent);
  outline: 1px solid var(--color-accent);
}

.search-button {
  padding: 0.5em 1em;
  font-size: 0.9em;
  background-color: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
  border-radius: 4px;
  cursor: pointer;
}

.search-button:hover {
  background-color: var(--color-accent-hover);
}
</style>
