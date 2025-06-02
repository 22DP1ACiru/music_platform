<script setup lang="ts">
import { RouterLink } from "vue-router";

const props = defineProps<{
  order_id?: string;
  token?: string;
}>();

// You could potentially use props.order_id to fetch the order and display its details
// or offer to retry payment if the order is still PENDING.
// For now, a simple cancellation message.
</script>

<template>
  <div class="payment-status-view">
    <h2>Payment Cancelled</h2>
    <div class="cancel-message">
      <p>Your payment process was cancelled.</p>
      <p v-if="props.order_id">
        Your order #{{ props.order_id }} has not been completed.
      </p>
      <p>You can return to your cart or continue shopping.</p>
      <div class="actions">
        <RouterLink :to="{ name: 'cart' }" class="action-button"
          >View Cart</RouterLink
        >
        <RouterLink :to="{ name: 'home' }" class="action-button secondary"
          >Continue Shopping</RouterLink
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.payment-status-view {
  max-width: 600px;
  margin: 3rem auto;
  padding: 2rem;
  text-align: center;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}
.payment-status-view h2 {
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}
.cancel-message p {
  margin-bottom: 0.75rem;
  line-height: 1.6;
}
.actions {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
  gap: 1rem;
}
.action-button {
  padding: 0.7em 1.5em;
  border-radius: 5px;
  text-decoration: none;
  font-weight: 500;
  background-color: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
}
.action-button.secondary {
  background-color: var(--color-background-mute);
  color: var(--color-text);
  border-color: var(--color-border);
}
.action-button:hover {
  opacity: 0.9;
}
</style>
