import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("../views/general/HomeView.vue"),
    },
    {
      path: "/about",
      name: "about",
      component: () => import("../views/general/AboutView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/auth/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../views/auth/RegisterView.vue"),
    },
    {
      path: "/releases",
      name: "releases",
      component: () => import("../views/release/ReleaseListView.vue"),
    },
    {
      path: "/releases/:id",
      name: "release-detail",
      component: () => import("../views/release/ReleaseDetailView.vue"),
      props: true,
    },
    {
      path: "/artists/:id",
      name: "artist-detail",
      component: () => import("../views/artist/ArtistDetailView.vue"),
      props: true,
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("../views/profile/ProfileView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/artist/create",
      name: "artist-create",
      component: () => import("../views/artist/CreateArtistView.vue"),
      meta: { requiresAuth: true, requiresArtistCreation: true },
    },
    {
      path: "/release/create",
      name: "release-create",
      component: () => import("../views/release/CreateReleaseView.vue"),
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/release/edit/:id",
      name: "release-edit",
      component: () => import("../views/release/EditReleaseView.vue"),
      props: true,
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/library",
      name: "library",
      component: () => import("../views/library/LibraryView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/orders",
      name: "order-history",
      component: () => import("../views/order/OrderHistoryView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/cart",
      name: "cart",
      component: () => import("../views/cart/CartView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/order/confirm/:orderId",
      name: "order-confirm",
      component: () => import("../views/order/OrderConfirmView.vue"),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: "/chat",
      name: "chat-list",
      component: () => import("../views/chat/ChatListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/chat/:conversationId",
      name: "chat-conversation",
      component: () => import("../views/chat/ChatConversationView.vue"),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: "/playlists/my",
      name: "my-playlists",
      component: () => import("../views/playlist/MyPlaylistsView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/playlists/create",
      name: "playlist-create",
      component: () => import("../views/playlist/CreatePlaylistView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/playlists/:id",
      name: "playlist-detail",
      component: () => import("../views/playlist/PlaylistDetailView.vue"),
      props: true,
    },
    {
      path: "/search",
      name: "search-results",
      component: () => import("../views/general/SearchView.vue"),
      props: (route) => ({ query: route.query.q }),
    },
    // Admin Routes
    {
      path: "/admin",
      name: "admin-dashboard",
      component: () => import("../views/admin/AdminDashboardView.vue"),
      meta: { requiresAuth: true, requiresStaff: true },
      children: [
        {
          path: "highlights",
          name: "admin-highlights",
          component: () =>
            import("../views/admin/highlights/AdminHighlightListView.vue"),
        },
        {
          path: "highlights/new",
          name: "admin-highlight-create",
          component: () =>
            import("../views/admin/highlights/AdminHighlightCreateView.vue"),
        },
        {
          path: "highlights/edit/:highlightId", // Use highlightId to avoid conflict with other :id
          name: "admin-highlight-edit",
          component: () =>
            import("../views/admin/highlights/AdminHighlightEditView.vue"),
          props: true,
        },
        // Add more admin sub-routes here later (e.g., for stats)
      ],
    },
    {
      path: "/order/payment/success",
      name: "payment-success",
      component: () => import("../views/order/PaymentSuccessView.vue"),
      props: (route) => ({
        order_id: route.query.order_id,
        paypal_payment_id: route.query.paypal_payment_id, // If PayPal adds this (check actual redirect)
        token: route.query.token, // PayPal often adds a token
        PayerID: route.query.PayerID, // And a PayerID
      }),
      meta: { requiresAuth: true }, // User should be logged in to see their order status
    },
    {
      path: "/order/payment/cancel",
      name: "payment-cancel",
      component: () => import("../views/order/PaymentCancelView.vue"),
      props: (route) => ({
        order_id: route.query.order_id,
        token: route.query.token,
      }),
      meta: { requiresAuth: true }, // User should be logged in
    },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (
    (!authStore.isLoggedIn && localStorage.getItem("accessToken")) ||
    (authStore.isLoggedIn && !authStore.authUser) // Check if user object is missing despite token
  ) {
    if (!authStore.authLoading) {
      await authStore.tryAutoLogin(router);
    }
  }

  // Wait for any ongoing authentication process to complete
  while (authStore.authLoading) {
    await new Promise((resolve) => setTimeout(resolve, 50));
  }

  const isLoggedIn = authStore.isLoggedIn;
  const isStaffUser = authStore.isStaff; // Use the computed property from store

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresStaff = to.matched.some((record) => record.meta.requiresStaff);
  const requiresArtist = to.matched.some(
    (record) => record.meta.requiresArtist
  );
  const requiresArtistCreation = to.matched.some(
    (record) => record.meta.requiresArtistCreation
  );

  if (
    (requiresAuth ||
      requiresStaff ||
      requiresArtist ||
      requiresArtistCreation) &&
    !isLoggedIn
  ) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (requiresStaff && !isStaffUser) {
    alert("You do not have permission to access this page.");
    next({ name: "home" }); // Or some other appropriate redirect
  } else if (requiresArtist && !authStore.hasArtistProfile) {
    alert("You need an artist profile to access this page.");
    next({ name: "profile" });
  } else if (requiresArtistCreation && authStore.hasArtistProfile) {
    alert("You already have an artist profile.");
    next({
      name: "artist-detail",
      params: { id: authStore.artistProfileId || "0" },
    });
  } else {
    next();
  }
});

export default router;
