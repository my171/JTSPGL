import { createRouter, createWebHistory } from 'vue-router'
import Page1 from '@/views/Page1.vue'
import Page2 from '@/views/Page2.vue'

const routes = [
  { path: '/', redirect: '/page1' },
  { path: '/page1', component: Page1 },
  { path: '/page2', component: Page2 },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
