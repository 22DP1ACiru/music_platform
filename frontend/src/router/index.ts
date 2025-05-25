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
  ],
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Ensure auth store is initialized, especially if tryAutoLogin is not fully complete yet
  // This is important for direct navigations or page reloads.
  if (!authStore.user && localStorage.getItem("accessToken")) {
    // If user state is not set but a token exists, try to auto-login/fetch user
    // This ensures user data (including profile) is loaded before guards run.
    // Consider if tryAutoLogin should return a promise to await here.
    // For now, this will trigger the fetch. Subsequent checks will use the populated store.
    if (!authStore.isLoading) {
      // Avoid multiple calls if already loading
      await authStore.tryAutoLogin();
    }
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresArtist = to.matched.some(
    (record) => record.meta.requiresArtist
  );
  // Meta field for routes like 'artist-create' that should only be accessible if user DOES NOT have an artist profile yet
  const requiresArtistCreation = to.matched.some(
    (record) => record.meta.requiresArtistCreation
  );

  if (requiresAuth && !authStore.isLoggedIn) {
    next({ name: "login", query: { redirect: to.fullPath } });
  } else if (requiresArtist) {
    if (!authStore.isLoggedIn) {
      // Should be caught by requiresAuth
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (authStore.isLoading) {
      // If user data is still loading
      // Option 1: Wait for loading to finish
      // This might require a watcher or a promise from tryAutoLogin/fetchUser
      // Option 2: Redirect to a loading page or home, and let user retry
      // For simplicity, let's retry navigation after a short delay or redirect to home
      // This is a temporary measure; robust solution would await user load.
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtist check. Retrying or redirecting."
      );
      // Simple approach: Redirect to home, user can click again.
      // A better UX would be to show a global loading indicator and truly wait.
      next({ name: "home" }); // Or handle loading state more gracefully
    } else if (!authStore.hasArtistProfile) {
      alert(
        "You need an artist profile to access this page. Please create one from your profile."
      );
      next({ name: "profile" });
    } else {
      next(); // Has artist profile
    }
  } else if (requiresArtistCreation) {
    if (!authStore.isLoggedIn) {
      next({ name: "login", query: { redirect: to.fullPath } });
    } else if (authStore.isLoading) {
      console.warn(
        "Navigation guard: User/profile data still loading for requiresArtistCreation check."
      );
      next({ name: "home" });
    } else if (authStore.hasArtistProfile) {
      alert("You already have an artist profile.");
      // Redirect to their artist detail page or profile
      next({
        name: "artist-detail",
        params: { id: authStore.artistProfileId },
      });
    } else {
      next(); // Does NOT have artist profile, so allow creation
    }
  } else {
    next();
  }
});

export default router;
