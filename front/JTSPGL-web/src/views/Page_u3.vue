<!--Page_u3.vue-->
<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧替换为商店操作界面 -->
      <div class="col-md-9 left-panel">
        <HeaderTime />
        <StoreOpPanel @new-approval="handleNewApproval" />
        <ChatBox />
      </div>

      <!-- 右侧审批流 -->
      <RightPanel
        ref="rightPanel"
        :approvalRequests="approvalRequests"
        @show-approval="showApprovalDetail"
      />
    </div>

    <!-- 弹窗 -->
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
import StoreOpPanel from "@components/StoreOpPanel.vue";

const rightPanel = ref(null);
const popupApproval = ref(null);
const approvalRequests = reactive([]);
const selectedApprovalId = ref(null);

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
.left-panel {
  height: 100vh;
  padding: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
</style>
