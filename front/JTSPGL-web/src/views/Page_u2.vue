<!-- Page_u2.vue -->
<template>
  <div class="container-fluid h-100 d-flex flex-column">
    <div class="row flex-grow-1 overflow-hidden">
      <!-- 左侧：仓库操作界面和聊天区域 -->
      <div class="col-md-9 d-flex flex-column px-3 py-3" style="position: relative; z-index: 0;">
        <HeaderTime />
        <WarehouseOpPanel @new-approval="handleNewApproval" />

        <!-- ChatBox 区域 -->
        <div class="chat-container mt-3 mb-4"> <!-- mb-4 提供底部留白 -->
          <ChatBox />
        </div>
      </div>

      <!-- 右侧面板 -->
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
import WarehouseOpPanel from "@components/WarehouseOpPanel.vue";

const rightPanel = ref(null);
const popupApproval = ref(null);

const approvalRequests = reactive([]); // 所有审批流记录


const warehouseName = localStorage.getItem("DetailInfo");

const filteredApprovals = computed(() => {
  return approvalRequests;//.filter(a => true); // 仍然返回普通数组，但 computed 会追踪依赖
});

// 新增审批记录

const handleNewApproval = (record) => {
  approvalRequests.push(record);
};

// 显示审批详情弹窗
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

.chat-container {
  width: 96%; /* 微微缩窄 */
  margin: 0 auto; /* 水平居中 */
  padding: 0;
}

.chat-box {
  height: 320px !important; /* 提高高度 */
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

</style>