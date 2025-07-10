<!-- PopupApproval.vue -->
<template>
    <div class="popup-panel" :class="{ show: isVisible }">
      <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">关闭</button>
      <div v-html="content"></div>
    </div>
  </template>
  
  <script setup>
  import { ref } from 'vue';
  
  const emit = defineEmits(['close']);
  
  const isVisible = ref(false);
  const content = ref('');
  
  const infoMap = {
    P10001: {
      status: "待审核",
      decisionTime: "-",
      reviewTime: "-",
      dispatchTime: "-",
      receivedTime: "-",
      from: "华东智能仓",
      to: "南京新街口店",
    },
    P10006: {
      status: "已完成",
      decisionTime: "2025-07-01 10:00",
      reviewTime: "2025-07-02 11:00",
      dispatchTime: "2025-07-03 15:30",
      receivedTime: "2025-07-05 09:15",
      from: "华北中心仓",
      to: "北京王府井旗舰店",
    },
    P10002: {
      status: "审核不通过",
      decisionTime: "2025-06-28 14:00",
      reviewTime: "2025-06-29 09:30",
      dispatchTime: "-",
      receivedTime: "-",
      from: "华南枢纽仓",
      to: "广州天河城店",
    },
    // 其他数据省略...
  };
  
  const show = (productId) => {
    const item = infoMap[productId] || {
      status: "未知",
      decisionTime: "-",
      reviewTime: "-",
      dispatchTime: "-",
      receivedTime: "-",
      from: "-",
      to: "-",
    };
  
    const html = `
      <h5>审批详情：${productId}</h5>
      <p><strong>当前状态：</strong>${item.status}</p>
      <p><strong>调出仓库：</strong>${item.from}</p>
      <p><strong>调入商店：</strong>${item.to}</p>
      <p><strong>决策时间：</strong>${item.decisionTime}</p>
      <p><strong>审核时间：</strong>${item.reviewTime}</p>
      <p><strong>发货时间：</strong>${item.dispatchTime}</p>
      <p><strong>收货时间：</strong>${item.receivedTime}</p>
    `;
    content.value = html;
    isVisible.value = true;
  };
  
  const close = () => {
    isVisible.value = false;
    emit('close');
  };

  const relatedclose = () => {
    isVisible.value = false;
  };
  
  defineExpose({ show, relatedclose });
  </script>
  
  <style scoped>
  @import './popup-style.css';
  </style>
  