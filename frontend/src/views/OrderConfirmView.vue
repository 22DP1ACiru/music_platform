<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useOrderStore } from "@/stores/order";

const route = useRoute();
const router = useRouter();
const orderStore = useOrderStore();

const orderId = computed(() => route.params.orderId as string);
const order = computed(() => orderStore.currentOrder);
const isLoading = computed(() => orderStore.isLoadingSingle);
const error = computed(() => orderStore.singleOrderError);

onMounted(() => {
  if (orderId.value) {
    orderStore.fetchOrderById(orderId.value);
  }
});

const handleConfirmPayment = async () => {
  if (order.value && order.value.status === "PENDING") {
    const success = await orderStore.confirmOrderPayment(order.value.id);
    if (success) {
      alert(
        "Payment confirmed! Your order is complete and items have been added to your library."
      );
      // The orderStore.confirmOrderPayment now updates currentOrder,
      // so the view will reactively show the 'COMPLETED' status.
      // We might want to navigate to order history or library.
      router.push({ name: "library" }); // Or order-history
    } else {
      // Error is handled by the store and displayed via `error` computed prop
      alert(
        `Failed to confirm payment: ${
          orderStore.singleOrderError || "Unknown error"
        }`
      );
    }
  } else if (order.value) {
    alert(
      `This order is already ${
        order.value.status_display || order.value.status
      }.`
    );
  }
};

const formatCurrency = (
  amount: string | undefined,
  currencyCode: string | undefined
) => {
  if (amount === undefined || currencyCode === undefined) return "N/A";
  const numericAmount = parseFloat(amount);
  if (isNaN(numericAmount)) return amount;
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currencyCode,
  }).format(numericAmount);
};

const formatDate = (dateString: string | undefined) => {
  if (!dateString) return "N/A";
  return new Date(dateString).toLocaleString();
};
</script>

<template>
  <div class="order-confirm-view">
    <h2>Order Confirmation</h2>

    <div v-if="isLoading" class="loading-message">Loading order details...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="!order" class="error-message">Order details not found.</div>

    <div v-else class="order-details-card">
      <h3>Order #{{ order.id }} Summary</h3>
      <p class="order-status-line">
        Status:
        <span :class="`status-badge status-${order.status.toLowerCase()}`">{{
          order.status_display || order.status
        }}</span>
      </p>
      <p>Placed on: {{ formatDate(order.created_at) }}</p>
      <p class="total-amount">
        Total: {{ formatCurrency(order.total_amount, order.currency) }}
      </p>

      <h4>Items:</h4>
      <ul class="items-list">
        <li v-for="item in order.items" :key="item.id" class="item-entry">
          <span class="item-name">{{ item.product.name }}</span>
          <span class="item-quantity">Qty: {{ item.quantity }}</span>
          <span class="item-price-at-purchase">
            {{ formatCurrency(item.price_at_purchase, order.currency) }}
          </span>
        </li>
      </ul>

      <div v-if="order.status === 'PENDING'" class="payment-actions">
        <button @click="handleConfirmPayment" class="confirm-payment-btn">
          Confirm & Pay (Simulated)
        </button>
      </div>
      <div v-else-if="order.status === 'COMPLETED'" class="completion-message">
        <p>✅ This order is complete. Items have been added to your library.</p>
        <router-link :to="{ name: 'library' }" class="action-button"
          >Go to My Library</router-link
        >
      </div>
      <div v-else class="completion-message">
        <p>
          This order is currently {{ order.status_display || order.status }}.
        </p>
        <router-link :to="{ name: 'order-history' }" class="action-button"
          >View Order History</router-link
        >
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-confirm-view {
  max-width: 700px;
  margin: 2rem auto;
  padding: 1rem;
}
.order-confirm-view h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: var(--color-heading);
}

.loading-message {
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
  text-align: center;
}

.order-details-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 2rem;
}
.order-details-card h3 {
  margin-top: 0;
  margin-bottom: 1rem;
  font-size: 1.4em;
  border-bottom: 1px solid var(--color-border-hover);
  padding-bottom: 0.5rem;
}
.order-details-card p {
  margin: 0.5rem 0;
  font-size: 1em;
  color: var(--color-text);
}
.total-amount {
  font-weight: bold;
  font-size: 1.2em;
  margin-top: 1rem;
}

.order-status-line {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}
.status-badge {
  font-size: 0.9em;
  font-weight: bold;
  padding: 0.2em 0.6em;
  border-radius: 4px;
  text-transform: capitalize;
  color: white; /* Default for most badges */
}
.status-pending {
  background-color: #ffc107;
  color: #333;
}
.status-completed {
  background-color: #28a745;
}
.status-failed {
  background-color: #dc3545;
}
/* Add other statuses as needed */

.items-list {
  list-style: none;
  padding: 0;
  margin-top: 0.5rem;
  margin-bottom: 1.5rem;
}
.item-entry {
  display: flex;
  justify-content: space-between;
  padding: 0.6rem 0;
  border-bottom: 1px solid var(--color-border-hover);
  font-size: 0.95em;
}
.item-entry:last-child {
  border-bottom: none;
}
.item-name {
  flex-grow: 1;
}
.item-quantity {
  color: var(--color-text-light);
  margin: 0 1rem;
}
.item-price-at-purchase {
  min-width: 80px;
  text-align: right;
}

.payment-actions {
  margin-top: 2rem;
  text-align: center;
}
.confirm-payment-btn {
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border: none;
  padding: 0.8em 2em;
  font-size: 1.1em;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}
.confirm-payment-btn:hover {
  background-color: var(--color-accent-hover);
}
.confirm-payment-btn:disabled {
  background-color: var(--color-border);
  cursor: not-allowed;
}

.completion-message {
  margin-top: 1.5rem;
  padding: 1rem;
  background-color: var(--color-background-mute);
  border-radius: 4px;
  text-align: center;
}
.completion-message p {
  font-size: 1.05em;
  margin-bottom: 0.75rem;
}
.action-button {
  padding: 0.6em 1.2em;
  font-size: 0.95em;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  margin-top: 0.5rem;
  background-color: var(--color-accent);
  color: var(--vt-c-white);
  border: 1px solid var(--color-accent);
}
.action-button:hover {
  background-color: var(--color-accent-hover);
}
</style>
