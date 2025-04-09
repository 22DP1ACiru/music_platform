<script setup lang="ts">
import { useRoute } from "vue-router";
const route = useRoute();
</script>

<template>
  <div class="artist-detail-page">
    <h2>Artist Detail (ID: {{ route.params.id }})</h2>
    <p>Artist details will go here.</p>
    <router-link to="/releases">Back to Releases</router-link>
  </div>
</template>

<style scoped>
/* Add basic styles if needed */
</style>
