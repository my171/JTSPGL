<template>
  <div class="col-md-3 right-panel" :style="{ transform: panelTransform }">
    <h5>AI 实时预警</h5>
    <textarea class="form-control mb-3" rows="3" readonly>暂无预警</textarea>

    <h5 class="mt-4">审批流进度</h5>
    <div id="approval-status">
      <button
        v-for="item in approvalItems"
        :key="item.id"
        class="approval-button"
        :class="`status-${item.statusColor}`"
        @click="showApproval(item.id)"
      >
        商品 {{ item.id }} - {{ item.statusText }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['show-approval']);

const panelTransform = ref('translateX(0)');

const approvalItems = [
  { id: 'P10001', statusText: '待审核', statusColor: 'gray' },
  { id: 'P10002', statusText: '审核不通过', statusColor: 'red' },
  { id: 'P10003', statusText: '待出库', statusColor: 'yellow' },
  { id: 'P10005', statusText: '待收货', statusColor: 'yellow' },
  { id: 'P10004', statusText: '待收货', statusColor: 'yellow' },
  { id: 'P10006', statusText: '已完成', statusColor: 'green' },

];

const showApproval = (productId) => {
  emit('show-approval', productId);
};

const movePanel = () => {
  panelTransform.value = 'translateX(-200px)';
};

const resetPanel = () => {
  panelTransform.value = 'translateX(0)';
};

defineExpose({
  movePanel,
  resetPanel
});
</script>

<style scoped>
.right-panel {
  height: 100vh;
  background-color: #ffffff;
  border-left: 1px solid #ddd;
  padding: 20px;
  overflow-y: auto;
  transition: transform 0.3s ease-in-out;
}

.approval-button {
  width: 100%;
  text-align: left;
  display: inline-block;
  padding: 6px 12px;
  margin: 5px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  font-size: 14px;
  transition: 0.2s;
}

.status-gray {
  background-color: #e0e0e0;
  color: #333;
  border: 1px solid #bcbbbb;
  transition: transform 0.1s ease;
}

.status-gray:hover {
  background-color: #bcbbbb;
  color: #333;
  transform: scale(1.02);
}

.status-red {
  background-color: #f58b8b;
  color: #842029;
  border: 1px solid #f8c4c9;
  transition: transform 0.1s ease;
}

.status-red:hover {
  background-color: #f65c5c;
  color: #842029;
  transform: scale(1.02);
}

.status-yellow {
  background-color: #fff3cd;
  color: #664d03;
  border: 1px solid #f8e6a8;
  transition: transform 0.1s ease;
}

.status-yellow:hover {
  background-color: #f8e6a8;
  color: #664d03;
  transform: scale(1.02);
}

.status-green {
  background-color: #d1e7d4;
  color: #0f5132;
  border: 1px solid #b6e9d2;
  transition: transform 0.1s ease;
}

.status-green:hover {
  background-color: rgb(154, 226, 172);
  color: #0f5132;
  transform: scale(1.02);
}
</style>