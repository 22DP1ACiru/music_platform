<script setup lang="ts">
import { onMounted, computed } from "vue";
import { useOrderStore } from "@/stores/order";
import { useAuthStore } from "@/stores/auth";
// import { RouterLink } from "vue-router"; // RouterLink not explicitly used in template

const orderStore = useOrderStore();
const authStore = useAuthStore();

const orders = computed(() => orderStore.orders);
const isLoading = computed(() => orderStore.isLoading);
const error = computed(() => orderStore.error);

onMounted(() => {
  if (authStore.isLoggedIn) {
    orderStore.fetchOrders();
  }
});

const formatCurrency = (amount: string, currencyCode: string) => {
  const numericAmount = parseFloat(amount);
  if (isNaN(numericAmount)) return amount;
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currencyCode,
  }).format(numericAmount);
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString();
};
</script>

<template>
  <div class="order-history-view">
    <h2>My Order History</h2>

    <div v-if="isLoading" class="loading-message">Loading orders...</div>
    <div v-else-if="error" class="error-message">{{ error }}</div>
    <div v-else-if="orders.length === 0" class="empty-history">
      You haven't placed any orders yet.
    </div>

    <div v-else class="orders-list">
      <div v-for="order in orders" :key="order.id" class="order-card">
        <div class="order-header">
          <h3>Order #{{ order.id }}</h3>
          <span
            class="order-status"
            :class="`status-${order.status.toLowerCase()}`"
          >
            {{ order.status_display || order.status }}
            <!-- Use status_display if available -->
          </span>
        </div>
        <p class="order-date">Placed on: {{ formatDate(order.created_at) }}</p>
        <p class="order-total">
          Total: {{ formatCurrency(order.total_amount, order.currency) }}
        </p>

        <div class="order-items">
          <h4>Items:</h4>
          <ul v-if="order.items && order.items.length > 0">
            <li v-for="item in order.items" :key="item.id" class="order-item">
              <!-- CORRECTED LINE BELOW -->
              <span class="item-name">{{ item.product.name }}</span>
              <span class="item-qty">Qty: {{ item.quantity }}</span>
              <span class="item-price">
                Price:
                {{ formatCurrency(item.price_at_purchase, order.currency) }}
              </span>
            </li>
          </ul>
          <p v-else>No items information available for this order.</p>
        </div>
        <p v-if="order.payment_gateway_id" class="payment-info">
          Payment ID: {{ order.payment_gateway_id }}
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.order-history-view {
  max-width: 900px;
  margin: 2rem auto;
  padding: 1rem;
}
.order-history-view h2 {
  text-align: center;
  margin-bottom: 2rem;
}
.loading-message,
.empty-history {
  text-align: center;
  font-style: italic;
  padding: 2rem;
  color: var(--color-text-light);
}
.error-message {
  color: var(--vt-c-red-dark);
  background-color: var(--vt-c-red-soft);
  border: 1px solid var(--vt-c-red-dark);
  padding: 0.8rem;
  border-radius: 4px;
  margin-bottom: 1rem;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.order-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 1.5rem;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-border-hover);
}
.order-header h3 {
  margin: 0;
  font-size: 1.3em;
  color: var(--color-heading);
}
.order-status {
  font-size: 0.9em;
  font-weight: bold;
  padding: 0.2em 0.6em;
  border-radius: 4px;
  text-transform: capitalize;
}
.status-pending {
  background-color: #ffc107; /* Yellow for pending */
  color: #333;
}
.status-processing {
  background-color: #17a2b8; /* Info blue for processing */
  color: white;
}
.status-completed {
  background-color: #28a745; /* Green for completed */
  color: white;
}
.status-failed {
  background-color: #dc3545; /* Red for failed */
  color: white;
}
.status-cancelled {
  background-color: #6c757d; /* Gray for cancelled */
  color: white;
}
.status-refunded {
  background-color: #fd7e14; /* Orange for refunded */
  color: white;
}

.order-date,
.order-total {
  font-size: 0.95em;
  color: var(--color-text);
  margin: 0.3rem 0;
}
.order-total {
  font-weight: 600;
}

.order-items {
  margin-top: 1rem;
}
.order-items h4 {
  font-size: 1em;
  font-weight: 500;
  margin-bottom: 0.5rem;
}
.order-items ul {
  list-style: none;
  padding-left: 0;
}
.order-item {
  display: flex;
  justify-content: space-between;
  padding: 0.4rem 0;
  font-size: 0.9em;
  border-bottom: 1px solid var(--color-border-hover);
}
.order-item:last-child {
  border-bottom: none;
}
.item-name {
  flex-grow: 1;
}
.item-qty {
  margin-left: 1rem;
  color: var(--color-text-light);
}
.item-price {
  margin-left: 1rem;
  min-width: 100px;
  text-align: right;
}
.payment-info {
  font-size: 0.85em;
  color: var(--color-text-light);
  margin-top: 0.5rem;
}
</style>
