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
});

const ROLE_ADMIN = 'admin';
const ROLE_WAREHOUSE = 'wh';
const ROLE_STORE = 'st';

router.beforeEach((to, from, next) => {
  const isAuthed = localStorage.getItem('isAuthed') === 'true'
  const RoleType = localStorage.getItem('RoleType')
  
  if (to.name == 'auth'){
    next()
  }
  else if (!isAuthed){
    next({ name: 'auth' })
  }
  else if (to.meta.requiresAuth && to.meta.type == 1 && RoleType == ROLE_ADMIN) {
    next()
  }
  else if (to.meta.requiresAuth && to.meta.type == 2 && RoleType == ROLE_WAREHOUSE) {
    next()
  }
  else if (to.meta.requiresAuth && to.meta.type == 3 && RoleType == ROLE_STORE) {
    next()
  }
  else {
    next({ name: 'auth' })
  }
})


export default router
