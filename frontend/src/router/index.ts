import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";

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
      meta: { requiresAuth: true },
    },
  ],
});

export default router;
