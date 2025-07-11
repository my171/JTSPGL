<!--app.vue-->
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

    <!-- 3个独立的弹出面板组件 -->
     <PopupStore
      ref="popupStore"
      @close="closeWarehousePopup"
     
     />
    <PopupWarehouse 
      ref="popupWarehouse"
      @close="closeWarehousePopup" 
      @show-store="showStorePopup"
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
import PopupStore from '@components/PopupStore.vue';

const rightPanel = ref(null);
const popupStore = ref(null);
const popupWarehouse = ref(null);
const popupApproval = ref(null);

const showWarehouseInfo = (id, name) => {
  rightPanel.value.movePanel();
  popupWarehouse.value.show(id, name); 
  popupApproval.value.relatedclose(); 
  popupStore.value.relatedclose();
};

const showApprovalDetail = (productId) => {
  rightPanel.value.movePanel();
  popupApproval.value.show(productId); 
  popupWarehouse.value.relatedclose(); 
};

const showStorePopup = (storeName) => {
  rightPanel.value.movePanel();
  popupStore.value.show(storeName);
  popupWarehouse.value.relatedclose(); 
  popupApproval.value.relatedclose(); 
  console.log("显示商店弹窗：", storeName);
};

const closeStorePopup = () => {
  rightPanel.value.resetPanel();
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