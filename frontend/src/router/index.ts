import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/about",
      name: "about",
      component: () => import("../views/AboutView.vue"),
    },
    {
      path: "/login",
      name: "login",
      component: () => import("../views/LoginView.vue"),
    },
    {
      path: "/register",
      name: "register",
      component: () => import("../views/RegisterView.vue"),
    },
    {
      path: "/releases",
      name: "releases",
      component: () => import("../views/ReleaseListView.vue"),
    },
    {
      path: "/releases/:id",
      name: "release-detail",
      component: () => import("../views/ReleaseDetailView.vue"),
      props: true,
    },
    {
      path: "/artists/:id",
      name: "artist-detail",
      component: () => import("../views/ArtistDetailView.vue"),
      props: true,
    },
    {
      path: "/profile",
      name: "profile",
      component: () => import("../views/ProfileView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/artist/create",
      name: "artist-create",
      component: () => import("../views/CreateArtistView.vue"),
      meta: { requiresAuth: true, requiresArtistCreation: true },
    },
    {
      path: "/release/create",
      name: "release-create",
      component: () => import("../views/CreateReleaseView.vue"),
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/release/edit/:id",
      name: "release-edit",
      component: () => import("../views/EditReleaseView.vue"),
      props: true,
      meta: { requiresAuth: true, requiresArtist: true },
    },
    {
      path: "/library",
      name: "library",
      component: () => import("../views/LibraryView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/orders",
      name: "order-history",
      component: () => import("../views/OrderHistoryView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/cart",
      name: "cart",
      component: () => import("../views/CartView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/order/confirm/:orderId",
      name: "order-confirm",
      component: () => import("../views/OrderConfirmView.vue"),
      props: true,
      meta: { requiresAuth: true },
    },
    // --- CHAT ROUTES ---
    {
      path: "/chat",
      name: "chat-list",
      component: () => import("../views/ChatListView.vue"),
      meta: { requiresAuth: true },
    },
    {
      path: "/chat/new", // Define the path for creating a new chat
      name: "chat-create", // The name you're trying to navigate to
      component: () => import("../views/CreateChatView.vue"), // Create this component
      meta: { requiresAuth: true },
    },
    {
      path: "/chat/:conversationId",
      name: "chat-conversation",
      component: () => import("../views/ChatConversationView.vue"),
      props: true,
      meta: { requiresAuth: true },
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
