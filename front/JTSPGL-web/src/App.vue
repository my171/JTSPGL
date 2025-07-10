<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧：地图和聊天区域 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <WarehouseMap @show-warehouse="showWarehouseInfo" />
        <ChatBox />
      </div>

      <RightPanel 
        ref="rightPanel"
        @show-approval="showApprovalDetail" 
      />
    </div>

    <!-- 新增两个独立的弹出面板组件 -->
    <PopupWarehouse 
      ref="popupWarehouse"
      @close="closeWarehousePopup" 
    />
    <PopupApproval 
      ref="popupApproval"
      @close="closeApprovalPopup" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';

import HeaderTime from '@components/HeaderTime.vue';
import WarehouseMap from '@components/WarehouseMap.vue';
import ChatBox from '@components/ChatBox.vue';
import RightPanel from '@components/RightPanel.vue';
import PopupWarehouse from '@components/PopupWarehouse.vue';
import PopupApproval from '@components/PopupApproval.vue';

const rightPanel = ref(null);
const popupWarehouse = ref(null);
const popupApproval = ref(null);

const showWarehouseInfo = (id, name) => {
  rightPanel.value.movePanel();
  popupWarehouse.value.show(id, name); 
  popupApproval.value.relatedclose(); 
};

const showApprovalDetail = (productId) => {
  rightPanel.value.movePanel();
  popupApproval.value.show(productId); 
  popupWarehouse.value.relatedclose(); 
};

const closeWarehousePopup = () => {
  rightPanel.value.resetPanel();
};
const closeApprovalPopup = () => {
  rightPanel.value.resetPanel();
};
</script>

<style scoped>
/* 保留原有的样式 */
.left-panel {
  height: 100vh;
  padding: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>