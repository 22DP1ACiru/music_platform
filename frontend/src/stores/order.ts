// frontend/src/stores/order.ts
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import axios from "axios";
import type { OrderDetail } from "@/types"; // Assuming OrderDetail is in types/index.ts
import { useAuthStore } from "./auth";
import { useCartStore } from "./cart";
import { useLibraryStore } from "./library";

// Interface for the paginated response structure from DRF
interface PaginatedOrdersResponse {
  count: number;
  next: string | null;
  previous: string | null;
  results: OrderDetail[];
}

export const useOrderStore = defineStore("order", () => {
  const orders = ref<OrderDetail[]>([]);
  const currentOrder = ref<OrderDetail | null>(null);
  const isLoading = ref(false);
  const isLoadingSingle = ref(false);
  const error = ref<string | null>(null);
  const singleOrderError = ref<string | null>(null);

  const authStore = useAuthStore();

  async function fetchOrders() {
    if (!authStore.isLoggedIn) return;
    isLoading.value = true;
    error.value = null;
    orders.value = []; // Clear previous orders before fetching
    try {
      // Expect the paginated response structure
      const response = await axios.get<PaginatedOrdersResponse>(
        "/shop/orders/"
      );
      orders.value = response.data.results; // Assign the 'results' array
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
    isLoadingSingle.value = true;
    singleOrderError.value = null;
    try {
      const response = await axios.post<OrderDetail>(
        `/shop/orders/${orderId}/confirm-payment/`
      );
      currentOrder.value = response.data;

      const cartStore = useCartStore();
      cartStore.fetchCart();

      const libraryStore = useLibraryStore();
      libraryStore.fetchLibraryItems();

      const orderIndex = orders.value.findIndex(
        (o) => o.id === response.data.id
      );
      if (orderIndex !== -1) {
        orders.value[orderIndex] = response.data;
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
