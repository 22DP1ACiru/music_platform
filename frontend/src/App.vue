<script setup lang="ts">
import { RouterView, useRoute } from "vue-router";
import Navbar from "./components/layout/Navbar.vue"; // Updated import path
import AudioPlayer from "./components/player/AudioPlayer.vue"; // Updated import path
import { computed } from "vue";

const route = useRoute();

const routesWithoutPlayer = ["login", "register"];

const showAudioPlayer = computed(() => {
  return !routesWithoutPlayer.includes(route.name as string);
});
</script>

<template>
  <header>
    <Navbar />
  </header>

  <main>
    <RouterView />
  </main>

  <AudioPlayer v-if="showAudioPlayer" />

  <footer>
    <p>© {{ new Date().getFullYear() }} Vaultwave</p>
  </footer>
</template>

<style scoped>
header {
  line-height: 1.5;
  max-height: 100vh;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 2rem;
}

main {
  padding: 0 2rem;
  padding-bottom: 70px;
}

footer {
  margin-top: 2rem;
  padding-top: 1rem;
  border-top: 1px solid var(--color-border);
  text-align: center;
  color: var(--color-text);
  font-size: 0.9em;
}
</style>
