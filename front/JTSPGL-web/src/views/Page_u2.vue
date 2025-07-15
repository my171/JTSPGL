<!-- Page_u2.vue -->
<template>
  <div class="container-fluid h-100 d-flex flex-column">
    <div class="row flex-grow-1 overflow-hidden">
      <!-- 左侧：仓库操作界面和聊天区域 -->
      <div class="col-md-9 d-flex flex-column px-3 py-3" style="position: relative;">
        <HeaderTime />
        <WarehouseOpPanel @new-approval="handleNewApproval" />

        <!-- ChatBox 区域 -->
        <div class="mt-3 mb-4"> <!-- mb-4 提供底部留白 -->
          <ChatBox />
        </div>
      </div>

      <!-- 右侧面板 -->
      <RightPanel
        ref="rightPanel"
        :approvalRequests="approvalRequests"
        @show-approval="showApprovalDetail"
      />
    </div>
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