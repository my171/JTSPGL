<!--
<template>
  <div class="page">
    <h1>页面 1</h1>
    <div class="buttons">
      <button @click="goToPage2">前往页面 2</button>
      <button @click="goToPage3">前往页面 3</button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const goToPage2 = () => {
  router.push('/page2')
}

const goToPage3 = () => {
  router.push('/page3')
}
</script>

<style scoped>
.page {
  text-align: center;
  padding: 2rem;
  background-color: #f0f8ff;
  min-height: 100vh;
}
.buttons {
  margin-top: 2rem;
}
button {
  margin: 0 1rem;
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
  cursor: pointer;
  background-color: #4a6fa5;
  color: white;
  border: none;
  border-radius: 4px;
  transition: background-color 0.3s;
}
button:hover {
  background-color: #3a5a80;
}
</style>
-->


<template>
  <div class="page1">
    <ClockBlock />
    <ChatBox />
    <!--ClockBlock/-->
  </div>
</template>

<script setup>
  import ChatBox from '@/components/ChatBox.vue';
import ClockBlock from '@components/ClockBlock.vue';
</script>

<style>
body {
  font-family: Arial, sans-serif;
  background-color: #f5f5f5;
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  margin: 0;
}

.app {
  width: 100%;
  display: flex;
  justify-content: center;
}
</style>