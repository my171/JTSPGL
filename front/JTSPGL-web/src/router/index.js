import { createRouter, createWebHistory } from 'vue-router'
import Page1 from '@/views/Page1.vue'

const routes = [
  { path: '/', redirect: '/page1' },
  { path: '/page1', component: Page1 },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
