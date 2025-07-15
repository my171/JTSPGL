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

//role definition
const ROLE_ADMIN = 'admin';
const ROLE_WAREHOUSE = 'wh';
const ROLE_STORE = 'st';


/*
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
*/
/*
  // 如果访问的是登录页
  if (to.name === 'auth') {
    if (isAuthed) {
      // 已登录则跳转对应角色页面
      switch (RoleType) {
        case ROLE_ADMIN:
          next({ path: '/page_USER1' });
          break;
        case ROLE_WAREHOUSE:
          next({ path: '/page_USER2' });
          break;
        case ROLE_STORE:
          next({ path: '/page_USER3' });
          break;
        default:
          next();
      }
    } else {
      next(); // 未登录允许进入登录页
    }
  }
  // 如果访问的是受保护页面
  else if (to.meta.requiresAuth) {
    if (!isAuthed) {
      // 未登录 -> 登录页
      next({ name: 'auth' });
    } else {
      // 已登录，检查角色是否匹配目标页面类型
      if (
        (to.meta.type === 1 && RoleType === ROLE_ADMIN) ||
        (to.meta.type === 2 && RoleType === ROLE_WAREHOUSE) ||
        (to.meta.type === 3 && RoleType === ROLE_STORE)
      ) {
        next(); // 匹配成功，放行
      } else {
        // 不匹配 -> 登出 + 回登录页
        localStorage.removeItem('isAuthed');
        localStorage.removeItem('RoleType');
        alert('身份不匹配，请重新登录');
        next({ name: 'auth' });
      }
    }
  }
  // 其他情况放行
  else {
    next();
  }
});
*/

export default router
