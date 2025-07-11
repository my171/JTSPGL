import { createRouter, createWebHistory } from 'vue-router'
import Page_u1 from "@/views/Page_u1.vue";
import Page_u2 from "@/views/Page_u2.vue";
import Page_u3 from "@/views/Page_u3.vue";
import Page_AuthForm from '@/views/Page_AuthForm.vue'

const routes = [
  { path: "/", redirect: "/Page_AuthForm" },
  { path: "/page_USER1", component: Page_u1,
    meta: { requiresAuth: true, type: 1} },
  { path: "/page_USER2", component: Page_u2,
    meta: { requiresAuth: true, type: 2 } },
  { path: "/page_USER3", component: Page_u3,
    meta: { requiresAuth: true, type: 3 } },
  { path: "/Page_AuthForm",
    name: 'auth',
    component: Page_AuthForm ,
    meta: { requiresAuth: false } },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to, from, next) => {
  const isAuthenticated1 = localStorage.getItem('authenticated_UserType1') === 'true'
  const isAuthenticated2 = localStorage.getItem('authenticated_UserType2') === 'true'
  const isAuthenticated3 = localStorage.getItem('authenticated_UserType3') === 'true'
  
  if (to.name == 'auth'){
    next()
  }
  if (to.meta.requiresAuth && to.meta.type == 1 && isAuthenticated1) {
    next()
  }
  else if (to.meta.requiresAuth && to.meta.type == 2 && isAuthenticated2) {
    next()
  }
  else if (to.meta.requiresAuth && to.meta.type == 3 && isAuthenticated3) {
    next()
  }
  else {
    next({ name: 'auth' })
  }
})


export default router
