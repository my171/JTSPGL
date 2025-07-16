<!--Page_u3.vue-->
<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧替换为商店操作界面 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <StoreOpPanel @new-approval="handleNewApproval" />
        <div class="flex-grow-1 d-flex flex-column">
          <ChatBox />
        </div>
      </div>

      <!-- 右侧审批流 -->
      <RightPanel
        ref="rightPanel"
        :approvalRequests="filteredApprovals"
        @show-approval="showApprovalDetail"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from "vue";

import HeaderTime from "@components/HeaderTime.vue";
import ChatBox from "@components/ChatBox.vue";
import RightPanel from "@components/RightPanel.vue";
import PopupApproval from "@components/PopupApproval.vue";
import StoreOpPanel from "@components/StoreOpPanel.vue";

const rightPanel = ref(null);
const popupApproval = ref(null);

const approvalRequests = reactive([]);
const selectedApprovalId = ref(null);

const userRole = localStorage.getItem("user_role");
const warehouseName = localStorage.getItem("warehouse_name");
const storeName = localStorage.getItem("store_name");

// 权限过滤后的审批流
const filteredApprovals = computed(() => {
  return approvalRequests;
})

const handleNewApproval = (record) => {
  approvalRequests.push(record);
};

const showApprovalDetail = (id) => {
  rightPanel.value.movePanel();
  popupApproval.value.show(id);
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