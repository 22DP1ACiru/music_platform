import { defineStore } from "pinia";
import { ref } from "vue";
import axios from "axios";
import type { Product } from "@/stores/product"; // Assuming you might create this later or define inline

// Define interfaces based on your backend OrderSerializer
interface OrderItemDetail {
  id: number;
  product: number; // Product ID
  product_name: string;
  quantity: number;
  price_at_purchase: string; // Decimal as string
  item_total: string; // Decimal as string
}

export interface OrderDetail {
  id: number;
  user: number; // User ID
  user_username: string | null;
  email: string | null;
  total_amount: string; // Decimal as string
  currency: string;
  status: string;
  created_at: string;
  updated_at: string;
  payment_gateway_id: string | null;
  items: OrderItemDetail[];
}

export const useOrderStore = defineStore("order", () => {
  const orders = ref<OrderDetail[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchOrders() {
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

  // Placeholder for creating an order - actual creation happens in ReleaseDetailView for now
  // async function createOrder(payload: any) { /* ... */ }

  return {
    orders,
    isLoading,
    error,
    fetchOrders,
  };
});
