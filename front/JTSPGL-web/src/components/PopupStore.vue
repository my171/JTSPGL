<!--PopupStore.vue-->
<template>
    <div class="popup-panel" :class="{ show: isVisible }">
      <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">关闭</button>
      <h5>商店：{{ storeName }}</h5>
      <p>这里可以显示商店相关信息，例如商品列表、销售记录等</p>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  
  const isVisible = ref(false);
  const storeName = ref('');
  
  const emit = defineEmits(['close']);
  
  const show = (name) => {
    storeName.value = name;
    isVisible.value = true;
  };
  
  const close = () => {
    isVisible.value = false;
    emit('close');
  };
  
  defineExpose({ show });
  </script>
  
  <style scoped>
  @import './popup-style.css';
  </style>
  