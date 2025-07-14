<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧：仓库操作界面和聊天区域 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <WarehousePanel />
        <ChatBox />
      </div>

      <RightPanel
        ref="rightPanel"
        :approvalRequests="approvalRequests"
        @show-approval="showApprovalDetail"
      />
    </div>

    <!-- 弹出面板 -->
    
    <PopupApproval
      ref="popupApproval"
      :approvalRequests="approvalRequests"
      :selectedApprovalId="selectedApprovalId"
      @close="closeApprovalPopup"
    />
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";

import HeaderTime from "@components/HeaderTime.vue";
import WarehouseMap from "@components/WarehouseMap.vue";
import ChatBox from "@components/ChatBox.vue";
import RightPanel from "@components/RightPanel.vue";
import PopupWarehouse from "@components/PopupWarehouse.vue";
import PopupApproval from "@components/PopupApproval.vue";
import PopupStore from "@components/PopupStore.vue";

const rightPanel = ref(null);
const popupStore = ref(null);
const popupWarehouse = ref(null);
const popupApproval = ref(null);

const approvalRequests = reactive([]); // 所有审批流记录
const selectedApprovalId = ref(null);

const showWarehouseInfo = (id, name) => {
  rightPanel.value.movePanel();
  popupWarehouse.value.show(id, name);
  popupApproval.value.relatedclose();
  popupStore.value.relatedclose();
};

const showApprovalDetail = (approvalId) => {
  rightPanel.value.movePanel();
  popupApproval.value.show(approvalId);
  popupWarehouse.value.relatedclose();
  popupStore.value.relatedclose();
};

const showStorePopup = (storeName, storeId) => {
  rightPanel.value.movePanel();
  popupStore.value.show(storeName, storeId);
  popupWarehouse.value.relatedclose();
  popupApproval.value.relatedclose();
  console.log("显示商店弹窗：", storeName);
};

const handleNewApproval = (record) => {
  approvalRequests.push(record);
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
.left-panel {
  height: 100vh;
  padding: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>
