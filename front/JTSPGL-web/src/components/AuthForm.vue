<template>
  <div class="login-container">
    <h1>{{ title }}</h1>
    <form @submit.prevent="handleSubmit">
      <div class="input-group">
        <label for="username">用户名</label>
        <input
          type="text"
          id="username"
          v-model="form.username"
          class="input-field"
          placeholder="请输入用户名"
          required
        />
      </div>
      <div class="input-group">
        <label for="password">密码</label>
        <input
          type="password"
          id="password"
          v-model="form.password"
          class="input-field"
          placeholder="请输入密码"
          required
        />
      </div>
      <button type="submit" class="submit-btn">登录</button>
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import axios from "axios";
import router from '@/router'
import { showToast } from '@/utils/toast'

const props = defineProps({
  title: {
    type: String,
    default: '用户登录'
  }
});

const form = reactive({
  username: '',
  password: ''
});

const errorMessage = ref('');

const emit = defineEmits(['submit']);

const ROLE_ADMIN = 'admin';
const ROLE_WAREHOUSE = 'wh';
const ROLE_STORE = 'st';

const handleSubmit = async () => {
  // 简单的验证逻辑
  if (!form.username || !form.password) {
    errorMessage.value = '请输入用户名和密码';
    return;
  }
/*
  if (form.username === 'fslkgg' && form.password === 'fslkgg') {
    errorMessage.value = '';
    emit('submit', { success: true, data: form });
    localStorage.setItem('isAuthed', 'true');
    localStorage.setItem('RoleType', 'admin');
    await router.push('/page_USER1')
  } else  if (form.username === 'second' && form.password === '123456') {
    errorMessage.value = '';
    emit('submit', { success: true, data: form });
    localStorage.setItem('isAuthed', 'true');
    localStorage.setItem('RoleType', 'wh');
    await router.push('/page_USER2')
  } else  if (form.username === 'third' && form.password === '123456') {
    errorMessage.value = '';
    emit('submit', { success: true, data: form });
    localStorage.setItem('isAuthed', 'true');
    localStorage.setItem('RoleType', 'st');
    await router.push('/page_USER3')
  } else {
    errorMessage.value = '用户名或密码错误';
    emit('submit', { success: false, error: '验证失败' });
  }
*/

/*用户名admin,密码123456可以直接进入/USER1界面来着*/

  try {
    const response = await axios.post("http://localhost:5000/api/verify", {
      username: form.username,
      password: form.password,
    });

    if (response.data.success){
      errorMessage.value = '';
      localStorage.setItem('isAuthed', 'true');
      localStorage.setItem('RoleType', response.data.role);
      localStorage.setItem('DetailInfo', response.data.detail);
      switch(response.data.role){
        case ROLE_ADMIN:
          await router.push('/page_USER1');
          break;
        case ROLE_WAREHOUSE:
          await router.push('/page_USER2');
          break;
        case ROLE_STORE:
          await router.push('/page_USER3');
          break;
      }
    }
    else{
      errorMessage.value = '用户名或密码错误';
    }
  } catch (error) {
    alert(error);
    errorMessage.value = '服务器运行异常';
  }
  
};


/*
// 路由守卫
router.beforeEach((to, from, next) => {
  const isAuthed = localStorage.getItem('isAuthed') === 'true';
  const RoleType = localStorage.getItem('RoleType');

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
</script>

<style scoped>
.login-container {
  background-color: white;
  border-radius: 15px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  padding: 30px;
  width: 350px;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
}

.input-group {
  margin-bottom: 20px;
}

.input-field {
  width: 100%;
  padding: 12px 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  box-sizing: border-box;
  transition: border-color 0.3s;
}

.input-field:focus {
  border-color: #4a90e2;
  outline: none;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: bold;
}

.submit-btn {
  width: 100%;
  padding: 12px;
  background-color: #4a90e2;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.submit-btn:hover {
  background-color: #357ab8;
}

.error-message {
  color: #e74c3c;
  text-align: center;
  margin-top: 15px;
}
</style>