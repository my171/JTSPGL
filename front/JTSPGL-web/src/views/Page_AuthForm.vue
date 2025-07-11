<template>
  <div class="app">
    <AuthForm @submit="handleLogin" />
  </div>
</template>

<script setup>
import AuthForm from '@components/AuthForm.vue';

const handleLogin = (result) => {
  console.log('登录结果:', result);
};
</script>

<style>
.app {
  font-family: Arial, sans-serif;
  background-color: #f5f5f5;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  margin: 0;
  width: 100%;
  display: flex;
  justify-content: center;
}
</style>