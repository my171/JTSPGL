<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧：仓库操作界面和聊天区域 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <WarehouseOpPanel @new-approval="handleNewApproval" />
        <div class="flex-grow-1 d-flex flex-column">
          <ChatBox />
        </div>
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
import ChatBox from "@components/ChatBox.vue";
import RightPanel from "@components/RightPanel.vue";
import PopupApproval from "@components/PopupApproval.vue";
import WarehouseOpPanel from "@components/WarehouseOpPanel.vue";

const rightPanel = ref(null);
const popupApproval = ref(null);

const approvalRequests = reactive([]); // 所有审批流记录
const selectedApprovalId = ref(null);

const showApprovalDetail = (approvalId) => {
  rightPanel.value.movePanel();
  popupApproval.value.show(approvalId);
  popupWarehouse.value.relatedclose();
  popupStore.value.relatedclose();
};

const handleNewApproval = (record) => {
  approvalRequests.push(record);
};
const closeApprovalPopup = () => {
  rightPanel.value.resetPanel();
};
</script>

<style scoped>
html, body {
  overflow: hidden;
  height: 100%;
}

.left-panel {
  height: 100vh;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.left-panel > .row,
.left-panel > .container-fluid {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>