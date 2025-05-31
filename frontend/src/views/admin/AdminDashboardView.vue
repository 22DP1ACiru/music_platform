<script setup lang="ts">
import { RouterLink } from "vue-router";
</script>

<template>
  <div class="admin-dashboard-view">
    <h1>Admin Dashboard</h1>
    <nav class="admin-nav">
      <RouterLink :to="{ name: 'admin-highlights' }" class="admin-nav-link">
        Manage Highlights
      </RouterLink>
      <!-- Add more admin links here as features are built -->
      <!-- <RouterLink :to="{ name: 'admin-stats' }" class="admin-nav-link">
        View Statistics
      </RouterLink> -->
    </nav>
    <div class="admin-content">
      <p>Welcome to the admin area. Select a section to manage.</p>
      <router-view></router-view>
      <!-- For nested admin routes -->
    </div>
  </div>
</template>

<style scoped>
.admin-dashboard-view {
  padding: 1rem;
}
.admin-dashboard-view h1 {
  text-align: center;
  margin-bottom: 2rem;
  color: var(--color-heading);
}
.admin-nav {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--color-border);
}
.admin-nav-link {
  padding: 0.5rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  text-decoration: none;
  color: var(--color-text);
  background-color: var(--color-background-soft);
}
.admin-nav-link:hover,
.admin-nav-link.router-link-active {
  background-color: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}
.admin-content {
  padding: 1rem;
  background-color: var(--color-background-soft);
  border-radius: 4px;
}
</style>
