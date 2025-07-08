<template>
  <div class="header-time">{{ currentTime }}</div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const currentTime = ref('北京时间：');

const updateTime = () => {
  const now = new Date();
  currentTime.value = "北京时间：" + now.toLocaleString();
};

onMounted(() => {
  updateTime();
  setInterval(updateTime, 1000);
});
</script>

<style scoped>
.header-time {
  font-size: 28px;
  font-weight: bold;
  color: #333;
  text-align: center;
  margin-bottom: 10px;
}
</style>