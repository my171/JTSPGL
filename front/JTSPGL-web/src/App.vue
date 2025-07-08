<template>
  <div class="container-fluid">
    <div class="row">
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
    <PopupPanel 
      ref="popupPanel"
      @close="closePopup" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import HeaderTime from '@components/HeaderTime.vue';
import WarehouseMap from '@components/WarehouseMap.vue';
import ChatBox from '@components/ChatBox.vue';
import RightPanel from '@components/RightPanel.vue';
import PopupPanel from '@components/PopupPanel.vue';

const rightPanel = ref(null);
const popupPanel = ref(null);

const showWarehouseInfo = (id, name) => {
  rightPanel.value.movePanel();
  popupPanel.value.showWarehouseInfo(id, name);
};

const showApprovalDetail = (productId) => {
  rightPanel.value.movePanel();
  popupPanel.value.showApprovalDetail(productId);
};

const closePopup = () => {
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