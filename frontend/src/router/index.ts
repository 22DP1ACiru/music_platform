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
      path: "/order/confirm/:orderId", // Use orderId as a param
      name: "order-confirm",
      component: () => import("../views/OrderConfirmView.vue"),
      props: true, // Pass route params as props to the component
      meta: { requiresAuth: true },
    },
  ],
});

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore();

  if (!authStore.user && localStorage.getItem("accessToken")) {
    if (!authStore.authLoading) {
      await authStore.tryAutoLogin();
    }
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresArtist = to.matched.some(
    (record) => record.meta.requiresArtist
  );
  const requiresArtistCreation = to.matched.some(
    (record) => record.meta.requiresArtistCreation
  );

  if (requiresAuth && !authStore.isLoggedIn) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (requiresArtist) {
    if (!authStore.isLoggedIn) {
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (authStore.authLoading) {
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtist check."
      );
      // Allow navigation but content might briefly show loading state or be incomplete
      // Or redirect to a loading page, or wait for loading to finish.
      // For now, let's let it proceed and rely on views to handle loading state.
      next();
    } else if (!authStore.hasArtistProfile) {
      alert(
        "You need an artist profile to access this page. Please create one from your profile."
      );
      next({ name: "profile" });
    } else {
      next();
    }
  } else if (requiresArtistCreation) {
    if (!authStore.isLoggedIn) {
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (authStore.authLoading) {
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtistCreation check."
      );
      next(); // Allow navigation, view should handle loading state
    } else if (authStore.hasArtistProfile) {
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
