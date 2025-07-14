<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧：地图和聊天区域 -->
      <HeaderTime />
      <PopupStore
        ref="popupStore"
        @close="closeStorePopup"
        @new-approval="handleNewApproval"
      />
      <ChatBox />

    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";

import HeaderTime from "@components/HeaderTime.vue";
import WarehouseMap from "@components/WarehouseMap.vue";
import ChatBox from "@components/ChatBox.vue";
import PopupStore from "@components/PopupStore.vue";

const popupStore = ref(null);

const showWarehouseInfo = (id, name) => {
  popupStore.value.relatedclose();
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
