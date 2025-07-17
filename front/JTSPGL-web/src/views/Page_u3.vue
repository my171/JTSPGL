<!--Page_u3.vue-->
<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧替换为商店操作界面 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <div class="store-op-container mb-3" style="flex: 0 0 auto;">
          <StoreOpPanel 
            @new-approval="handleNewApproval" 
            @addwarn="addwarning" 
          />
        </div>
        <div class="chat-container">
          <ChatBox />
        </div>
      </div>

      <!-- 右侧审批流 -->
      <RightPanel
        ref="rightPanel"
        :approvalRequests="filteredApprovals"
        @show-approval="showApprovalDetail"
      />
      <PopupApproval
        ref="popupApproval"
        :approvalRequests="approvalRequests"
        @close="closeApprovalPopup"
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

const addwarning = (text) => {
  rightPanel.value.addwarning(text);
}
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


.store-op-container {
  min-height: 360px; /* 增加最小高度 */
  overflow-y: auto; /* 内容多时可滚动 */
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.chat-container .chat-box {
  height: 320px !important; /* 提升聊天框高度 */
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}


.left-panel > .row,
.left-panel > .container-fluid {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>