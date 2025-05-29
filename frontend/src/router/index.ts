import { createRouter, createWebHistory } from "vue-router";
// Removed HomeView import, will use dynamic import
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: () => import("../views/general/HomeView.vue"), // Path was already updated by user
    },
    {
      path: "/about",
      name: "about",
      component: () => import("../views/general/AboutView.vue"), // Path was already updated by user
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/auth/LoginView.vue"), // Path was already updated by user
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../views/auth/RegisterView.vue"), // Path was already updated by user
    },
    {
      path: "/releases",
      name: "releases",
      component: () => import("../views/release/ReleaseListView.vue"), // Updated path
    },
    {
      path: "/releases/:id",
      name: "release-detail",
      component: () => import("../views/release/ReleaseDetailView.vue"), // Updated path
      props: true,
    },
    {
      path: "/artists/:id",
      name: "artist-detail",
      component: () => import("../views/artist/ArtistDetailView.vue"), // Updated path
      props: true,
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("../views/profile/ProfileView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/artist/create",
      name: "artist-create",
      component: () => import("../views/artist/CreateArtistView.vue"), // Updated path
      meta: { requiresAuth: true, requiresArtistCreation: true },
    },
    {
      path: "/release/create",
      name: "release-create",
      component: () => import("../views/release/CreateReleaseView.vue"), // Updated path
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/release/edit/:id",
      name: "release-edit",
      component: () => import("../views/release/EditReleaseView.vue"), // Updated path
      props: true,
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/library",
      name: "library",
      component: () => import("../views/library/LibraryView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/orders",
      name: "order-history",
      component: () => import("../views/order/OrderHistoryView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/cart",
      name: "cart",
      component: () => import("../views/cart/CartView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/order/confirm/:orderId",
      name: "order-confirm",
      component: () => import("../views/order/OrderConfirmView.vue"), // Updated path
      props: true,
      meta: { requiresAuth: true },
    },
    // --- CHAT ROUTES ---
    {
      path: "/chat",
      name: "chat-list",
      component: () => import("../views/chat/ChatListView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/chat/:conversationId",
      name: "chat-conversation",
      component: () => import("../views/chat/ChatConversationView.vue"), // Updated path
      props: true,
      meta: { requiresAuth: true },
    },
    // --- PLAYLIST ROUTES ---
    {
      path: "/playlists/my",
      name: "my-playlists",
      component: () => import("../views/playlist/MyPlaylistsView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/playlists/create",
      name: "playlist-create",
      component: () => import("../views/playlist/CreatePlaylistView.vue"), // Updated path
      meta: { requiresAuth: true },
    },
    {
      path: "/playlists/:id",
      name: "playlist-detail",
      component: () => import("../views/playlist/PlaylistDetailView.vue"), // Updated path
      props: true,
    },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (
    (!authStore.isLoggedIn && localStorage.getItem("accessToken")) ||
    (authStore.isLoggedIn && !authStore.user)
  ) {
    if (!authStore.authLoading) {
      console.log("Router Guard: Attempting auto-login or user data fetch.");
      await authStore.tryAutoLogin(router);
    }
  }

  while (authStore.authLoading) {
    console.log(
      "Router Guard: Waiting for authentication/user data loading to complete..."
    );
    await new Promise((resolve) => setTimeout(resolve, 100));
  }

  const isLoggedIn = authStore.isLoggedIn;

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresArtist = to.matched.some(
    (record) => record.meta.requiresArtist
  );
  const requiresArtistCreation = to.matched.some(
    (record) => record.meta.requiresArtistCreation
  );

  if (requiresAuth && !isLoggedIn) {
    console.log(
      "Router Guard: requiresAuth=true, not logged in. Redirecting to login."
    );
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (requiresArtist) {
    if (!isLoggedIn) {
      console.log(
        "Router Guard: requiresArtist=true, not logged in. Redirecting to login."
      );
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (!authStore.hasArtistProfile) {
      console.log(
        "Router Guard: requiresArtist=true, logged in, but no artist profile. Redirecting to profile."
      );
      alert(
        "You need an artist profile to access this page. Please create one from your profile page."
      );
      next({ name: "profile" });
    } else {
      next();
    }
  } else if (requiresArtistCreation) {
    if (!isLoggedIn) {
      console.log(
        "Router Guard: requiresArtistCreation=true, not logged in. Redirecting to login."
      );
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (authStore.hasArtistProfile) {
      console.log(
        "Router Guard: requiresArtistCreation=true, but already has artist profile. Redirecting to artist detail."
      );
      alert("You already have an artist profile.");
      next({
        name: "artist-detail",
        params: { id: authStore.artistProfileId || "error" },
      });
    } else {
      next();
    }
  } else {
    next();
  }
});

export default router;
