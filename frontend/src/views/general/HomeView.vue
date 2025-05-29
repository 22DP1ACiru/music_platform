<script setup lang="ts">
import { ref } from "vue";

const welcomeMessage = ref("Welcome to Vaultwave!");
</script>

<template>
  <div class="home">
    <h1>{{ welcomeMessage }}</h1>
    <p>This is the Home Page.</p>
    <!-- Add more content for your home page here -->
  </div>
</template>

<style scoped>
/* Add CSS styles specific to the Home page here */
.home {
  text-align: center;
  padding: 40px;
}
</style>
