<script setup lang="ts">
import { RouterView } from "vue-router";
import Navbar from "./components/Navbar.vue";
import AudioPlayer from "./components/AudioPlayer.vue";
</script>

<template>
  <header>
    <Navbar />
  </header>

  <main>
    <RouterView />
  </main>

  <AudioPlayer />

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
