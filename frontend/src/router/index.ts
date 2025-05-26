// frontend/src/router/index.ts
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
  ],
});

router.beforeEach(async (to, _from, next) => {
  // Changed from to _from
  const authStore = useAuthStore();

  if (!authStore.user && localStorage.getItem("accessToken")) {
    // Use authLoading which is the correct name from the store
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
      // Use authLoading
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtist check."
      );
      next({ name: "home" });
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
      // Use authLoading
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtistCreation check."
      );
      next({ name: "home" });
    } else if (authStore.hasArtistProfile) {
      alert("You already have an artist profile.");
      next({
        name: "artist-detail",
        // Ensure artistProfileId is not null before using it
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
