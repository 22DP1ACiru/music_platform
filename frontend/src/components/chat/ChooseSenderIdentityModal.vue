<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { computed } from "vue";

const props = defineProps<{
  isVisible: boolean;
}>();

const emit = defineEmits<{
  (e: "identity-chosen", identity: "USER" | "ARTIST"): void;
  (e: "close"): void;
}>();

const authStore = useAuthStore();
const username = computed(() => authStore.authUser?.username);
const artistName = computed(
  () => authStore.authUser?.profile?.artist_profile_data?.name
);

const chooseIdentity = (identity: "USER" | "ARTIST") => {
  emit("identity-chosen", identity);
};

const closeModal = () => {
  emit("close");
};
</script>

<template>
  <div v-if="isVisible" class="identity-modal-overlay" @click.self="closeModal">
    <div class="identity-modal-content">
      <h4>Send message as:</h4>
      <button @click="chooseIdentity('USER')" class="identity-choice-button">
        Your User Account ({{ username }})
      </button>
      <button
        v-if="authStore.hasArtistProfile && artistName"
        @click="chooseIdentity('ARTIST')"
        class="identity-choice-button"
      >
        Your Artist Profile ({{ artistName }})
      </button>
      <button @click="closeModal" class="identity-cancel-button">Cancel</button>
    </div>
  </div>
</template>

<style scoped>
.identity-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1050;
}
.identity-modal-content {
  background-color: var(--color-background-soft);
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 90%;
  max-width: 400px;
  text-align: center;
}
.identity-modal-content h4 {
  margin-top: 0;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.identity-choice-button {
  display: block;
  width: 100%;
  padding: 0.8rem;
  margin-bottom: 0.75rem;
  font-size: 1em;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  cursor: pointer;
  background-color: var(--color-background);
  color: var(--color-text);
}
.identity-choice-button:hover {
  background-color: var(--color-background-mute);
  border-color: var(--color-border-hover);
}
.identity-cancel-button {
  margin-top: 1rem;
  padding: 0.6rem 1rem;
  background-color: var(--color-background-soft);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 5px;
  cursor: pointer;
}
.identity-cancel-button:hover {
  border-color: var(--vt-c-red);
  color: var(--vt-c-red);
}
</style>
