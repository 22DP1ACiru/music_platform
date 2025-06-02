<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useOrderStore } from "@/stores/order";
import { RouterLink } from "vue-router";

const props = defineProps<{
  order_id?: string;
  paypal_payment_id?: string; // If PayPal adds this to the URL
  token?: string;
  PayerID?: string;
}>();

const orderStore = useOrderStore();
const isLoadingOrder = ref(false);
const orderStatus = ref<string | null>(null);
const errorMessage = ref<string | null>(null);

onMounted(async () => {
  if (props.order_id) {
    isLoadingOrder.value = true;
    errorMessage.value = null;
    await orderStore.fetchOrderById(props.order_id);
    if (orderStore.currentOrder) {
      orderStatus.value =
        orderStore.currentOrder.status_display ||
        orderStore.currentOrder.status;
      // The webhook should ideally update the status to COMPLETED.
      // This page can re-fetch or just display a generic processing message.
      // If the webhook is fast, the status might already be COMPLETED here.
      if (orderStore.currentOrder.status !== "COMPLETED") {
        // Poll for a few seconds or instruct user to check library/orders
        // For simplicity, we'll just show current status.
        console.log(
          `PaymentSuccessView: Order ${props.order_id} status is ${orderStatus.value}. Webhook will finalize.`
        );
      }
    } else {
      errorMessage.value =
        orderStore.singleOrderError || "Could not retrieve order details.";
    }
    isLoadingOrder.value = false;
  } else {
    errorMessage.value = "Order ID not provided in redirect.";
  }
});
</script>

<template>
  <div class="payment-status-view">
    <h2>Payment Status</h2>

    <div v-if="isLoadingOrder" class="loading-message">
      Checking payment status...
    </div>
    <div v-else-if="errorMessage" class="error-message">
      <p>
        There was an issue retrieving your order details: {{ errorMessage }}
      </p>
      <p>
        Please check
        <RouterLink :to="{ name: 'order-history' }"
          >your order history</RouterLink
        >
        for the latest status.
      </p>
    </div>
    <div v-else-if="orderStore.currentOrder">
      <div
        v-if="orderStore.currentOrder.status === 'COMPLETED'"
        class="success-message"
      >
        <h3>Thank You! Your Payment was Successful!</h3>
        <p>Order #{{ orderStore.currentOrder.id }} is complete.</p>
        <p>
          Your items have been added to your library and your cart has been
          cleared.
        </p>
        <div class="actions">
          <RouterLink :to="{ name: 'library' }" class="action-button"
            >Go to My Library</RouterLink
          >
          <RouterLink
            :to="{ name: 'order-history' }"
            class="action-button secondary"
            >View Order History</RouterLink
          >
        </div>
      </div>
      <div v-else class="processing-message">
        <h3>Payment Processing</h3>
        <p>
          Your payment is being processed (Order #{{
            orderStore.currentOrder.id
          }}).
        </p>
        <p>Status: {{ orderStatus || "Processing..." }}</p>
        <p>
          You will be notified once it's complete, and items will be added to
          your library.
        </p>
        <p>
          If this status doesn't update soon, please check
          <RouterLink :to="{ name: 'order-history' }"
            >your order history</RouterLink
          >.
        </p>
        <div class="actions">
          <RouterLink :to="{ name: 'home' }" class="action-button"
            >Continue Shopping</RouterLink
          >
        </div>
      </div>
    </div>
    <div v-else class="error-message">
      <p>Could not load order details at this time.</p>
      <div class="actions">
        <RouterLink :to="{ name: 'home' }" class="action-button"
          >Go to Homepage</RouterLink
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
}
.loading-message {
  font-style: italic;
  color: var(--color-text-light);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red);
  padding: 1rem;
  border-radius: 4px;
}
.success-message h3 {
  color: #28a745; /* Green for success */
  margin-bottom: 1rem;
}
.processing-message h3 {
  color: var(--color-heading);
  margin-bottom: 1rem;
}
.success-message p,
.processing-message p {
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
