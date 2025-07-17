<template>
  <div class="container-fluid h-100 d-flex flex-column">
    <div class="row flex-grow-1 overflow-hidden">
      <!-- 左侧：地图和聊天区域 -->
      <div class="col-md-9 d-flex flex-column px-3 py-3">
        <HeaderTime />
        <WarehouseMap @show-warehouse="showWarehouseInfo" ref="warehouseMap" />

        <!-- 分隔条 -->
        <div
          class="resizer"
          @mousedown="startResizing"
          title="拖动以调整高度"
        ></div>

        <ChatBox class="chat-box" :style="{ height: chatBoxHeight + 'px' }" />
      </div>

      <RightPanel
        ref="rightPanel"
        :approvalRequests="approvalRequests"
        @show-approval="showApprovalDetail"
      />
    </div>

    <!-- 弹出面板 -->
    <PopupStore 
      ref="popupStore"
      @close="closeStorePopup" 
      @new-approval="handleNewApproval"
      @addwarn="addwarning" 
    />
    <PopupWarehouse
      ref="popupWarehouse"
      @close="closeWarehousePopup"
      @show-store="showStorePopup"
      @new-approval="handleNewApproval"
    />
    <PopupApproval
      ref="popupApproval"
      :approvalRequests="approvalRequests"
      @close="closeApprovalPopup"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from "vue";

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
const chatBoxHeight = ref(200); // 初始高度
const isResizing = ref(false);

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

const startResizing = (e) => {
  isResizing.value = true;
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", stopResizing);
};

const handleMouseMove = (e) => {
  if (!isResizing.value) return;

  // 当前鼠标 Y 坐标
  const mouseY = e.clientY;

  // ChatBox 的最小高度限制
  const minHeight = 100;
  // 页面总高度
  const totalHeight = window.innerHeight;

  // 计算 ChatBox 的高度 = 页面底部 - 鼠标 Y 坐标
  let newHeight = totalHeight - mouseY + 100;

  // 限制最小高度
  if (newHeight < minHeight) newHeight = minHeight;

  chatBoxHeight.value = newHeight;
}

const stopResizing = () => {
  isResizing.value = false;
  document.removeEventListener("mousemove", handleMouseMove);
  document.removeEventListener("mouseup", stopResizing);
};

// 清理事件监听器
onBeforeUnmount(() => {
  document.removeEventListener("mousemove", handleMouseMove);
  document.removeEventListener("mouseup", stopResizing);
});

const addwarning = (text) => {
  rightPanel.value.addwarning(text);
}
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

.resizer {
  height: 5px;
  background-color: #ccc;
  cursor: ns-resize;
  position: relative;
  z-index: 0;
  margin: 4px 0;
}

.resizer::after {
  content: "";
  position: absolute;
  top: -5px;
  left: 0;
  height: 15px;
  width: 100%;
  background-color: transparent;
  cursor: ns-resize;
  z-index: 1;
}
</style>
