<template>
  <div class="login-container">
    <h1 class="gradient-title">{{ title }}</h1>
    <form @submit.prevent="handleSubmit">
      <div class="input-group">
        
        <input
          type="text"
          id="username"
          v-model="form.username"
          class="input-field"
          required
          @focus="isUsernameFocused = true"
          @blur="isUsernameFocused = false"
        />
        <label for="username" :class="{ 'floating-label': true, 'active': isUsernameFocused || form.username }">
            用户名
        </label>
      </div>
      <div class="input-group" :class="{ 'focused': isPasswordFocused || form.password }">
  <input
    type="password"
    id="password"
    v-model="form.password"
    class="input-field"
    required
    @focus="isPasswordFocused = true"
    @blur="isPasswordFocused = false"
  />
  <label for="password" :class="{ 'floating-label': true, 'active': isPasswordFocused || form.password }">
    密码
  </label>
</div>
      <button type="submit" class="submit-btn">登录</button>
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    </form>
  </div>

  <!-- 登录成功动画卡片 -->
  <Transition name="fade-in-up">
  <div v-show="showLoginCard" class="login-card">
    <div class="card-content">
      <p>当前用户：{{ currentRoleName }}</p>
      <h3>登录成功</h3>
      <div class="loading-spinner"></div>
    </div>
  </div>
</Transition>
</template>

<script setup>
import { ref, reactive } from 'vue';
import axios from "axios";
import router from '@/router'
import { showToast } from '@/utils/toast'


const showLoginCard = ref(false);
const currentRoleName = ref('');

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


      // 设置角色名称
      if (response.data.role === ROLE_ADMIN) {
          currentRoleName.value = '系统管理员';
      } else if (response.data.role === ROLE_WAREHOUSE) {
        currentRoleName.value = '仓库管理系统'; // 如“华北中心仓”
      } else if (response.data.role === ROLE_STORE) {
        currentRoleName.value = '商店管理系统'; // 如“华北中心商店”
      }

      showLoginCard.value = true;

    
      setTimeout(async () => {
        showLoginCard.value = false;
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
      }, 2000);
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


const isUsernameFocused = ref(false);
const isPasswordFocused = ref(false);


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
  position: relative;
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
  outline: none;
}

.floating-label {
  position: absolute;
  left: 15px;
  top: 50%;
  transform: translateY(-50%);
  color: #999;
  font-size: 16px;
  background: white;
  padding: 0 5px;
  pointer-events: none;
  transition: all 0.3s ease;
  z-index: 1;
}

.floating-label.active {
  top: -10px;
  left: 10px;
  font-size: 12px;
  color: #4a90e2;
}


.fade-in-up-enter-active,
.fade-in-up-leave-active {
  transition: all 1s ease;
  transform: translate(-50%, -50%) scale(1);
  opacity: 1;
}

.fade-in-up-enter-from,
.fade-in-up-leave-to {
  transform: translate(-50%, -60%) scale(0.8);
  opacity: 0;
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
  background: linear-gradient(45deg, #518cea, #77b7f4);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}

.submit-btn:hover {
  background: linear-gradient(45deg, #3a76d8, #5ca2e6);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 87, 255, 0.35);
}

.error-message {
  color: #e74c3c;
  text-align: center;
  margin-top: 15px;
}

/*动画效果 */

.login-card {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: linear-gradient(135deg, #80bbf2, #d8eafb);
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  text-align: center;
  color: #555;
}

.card-content p,

.card-content h3 {
  margin: 10px 0;
  font-size: 20px;
  color: #555;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top: 4px solid #ffffff;
  border-radius: 50%;
  margin: 20px auto 0;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@keyframes fadeInZoom {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.8);
  }
  30% {
    opacity: 0.6;
    transform: translate(-50%, -50%) scale(1.05);
  }
  60% {
    opacity: 0.8;
    transform: translate(-50%, -50%) scale(0.95);
  }
  100% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}

.gradient-title {
  font-size: 24px;
  font-weight: bold;
  background: linear-gradient(45deg, #2d12e1, #77b7f4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-align: center;
  margin-bottom: 30px;
}

</style>