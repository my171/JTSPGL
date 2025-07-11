import { createRouter, createWebHistory } from 'vue-router'
import Page_u1 from "@/views/Page_u1.vue";
import Page_u2 from "@/views/Page_u2.vue";
import Page_u3 from "@/views/Page_u3.vue";
import Page2 from '@/views/Page2.vue'

const routes = [
  { path: "/", redirect: "/page_USER1" },
  { path: "/page_USER1", component: Page_u1 },
  { path: "/page_USER2", component: Page_u2 },
  { path: "/page_USER3", component: Page_u3 },
  { path: "/page2", component: Page2 },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
