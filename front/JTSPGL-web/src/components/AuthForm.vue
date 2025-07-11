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

const handleSubmit = () => {
  // 简单的验证逻辑
  if (!form.username || !form.password) {
    errorMessage.value = '请输入用户名和密码';
    return;
  }

  // 示例验证 - 实际项目中应该调用API
  if (form.username === 'admin' && form.password === '123456') {
    errorMessage.value = '';
    emit('submit', { success: true, data: form });
    alert('登录成功！');
  } else {
    errorMessage.value = '用户名或密码错误';
    emit('submit', { success: false, error: '验证失败' });
  }
};
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