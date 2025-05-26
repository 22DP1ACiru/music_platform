import { defineStore } from "pinia";
import { ref, computed } from "vue"; // Removed watch as it's not used here
import axios from "axios";
import type { OrderDetail } from "@/types"; // Assuming OrderDetail is in types/index.ts
import { useAuthStore } from "./auth";
import { useCartStore } from "./cart"; // For clearing cart after successful confirmation
import { useLibraryStore } from "./library"; // For refreshing library after successful confirmation

export const useOrderStore = defineStore("order", () => {
  const orders = ref<OrderDetail[]>([]);
  const currentOrder = ref<OrderDetail | null>(null); // For single order view
  const isLoading = ref(false);
  const isLoadingSingle = ref(false); // For single order loading
  const error = ref<string | null>(null);
  const singleOrderError = ref<string | null>(null); // For single order error

  const authStore = useAuthStore();
  // Note: To avoid potential circular dependencies if cartStore imports orderStore later,
  // it's sometimes safer to get store instances inside actions if only used there.
  // For now, this should be fine.

  async function fetchOrders() {
    if (!authStore.isLoggedIn) return;
    isLoading.value = true;
    error.value = null;
    orders.value = [];
    try {
      const response = await axios.get<OrderDetail[]>("/shop/orders/");
      orders.value = response.data;
    } catch (err) {
      console.error("Order Store: Failed to fetch orders:", err);
      if (axios.isAxiosError(err) && err.response?.status === 403) {
        error.value = "Please log in to view your order history.";
      } else {
        error.value = "Could not load your order history.";
      }
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchOrderById(orderId: number | string) {
    if (!authStore.isLoggedIn) return;
    isLoadingSingle.value = true;
    singleOrderError.value = null;
    currentOrder.value = null;
    try {
      const response = await axios.get<OrderDetail>(`/shop/orders/${orderId}/`);
      currentOrder.value = response.data;
    } catch (err) {
      console.error(`Order Store: Failed to fetch order ${orderId}:`, err);
      if (axios.isAxiosError(err) && err.response?.status === 404) {
        singleOrderError.value = "Order not found.";
      } else {
        singleOrderError.value = "Could not load order details.";
      }
    } finally {
      isLoadingSingle.value = false;
    }
  }

  async function confirmOrderPayment(
    orderId: number | string
  ): Promise<boolean> {
    if (!authStore.isLoggedIn) return false;
    isLoadingSingle.value = true; // Reuse loading state or have a specific one
    singleOrderError.value = null;
    try {
      const response = await axios.post<OrderDetail>(
        `/shop/orders/${orderId}/confirm-payment/`
      );
      currentOrder.value = response.data; // Update current order with confirmed details

      // Refresh relevant stores after successful confirmation
      const cartStore = useCartStore(); // Get instance here
      cartStore.fetchCart(); // To reflect cleared cart (backend clears it)

      const libraryStore = useLibraryStore(); // Get instance here
      libraryStore.fetchLibraryItems(); // To reflect new items in library

      // Optionally, refresh the full order list if needed, or update the specific order in the list
      const orderIndex = orders.value.findIndex(
        (o) => o.id === response.data.id
      );
      if (orderIndex !== -1) {
        orders.value[orderIndex] = response.data;
      } else {
        // If not in list, fetch all (or just add it if that's preferred)
        // fetchOrders(); // Could be heavy, but ensures consistency
      }

      return true;
    } catch (err) {
      console.error(
        `Order Store: Failed to confirm payment for order ${orderId}:`,
        err
      );
      if (axios.isAxiosError(err) && err.response) {
        singleOrderError.value =
          err.response.data.detail || "Payment confirmation failed.";
      } else {
        singleOrderError.value =
          "An unexpected error occurred during payment confirmation.";
      }
      return false;
    } finally {
      isLoadingSingle.value = false;
    }
  }

  return {
    orders,
    currentOrder,
    isLoading,
    isLoadingSingle,
    error,
    singleOrderError,
    fetchOrders,
    fetchOrderById,
    confirmOrderPayment,
  };
});
