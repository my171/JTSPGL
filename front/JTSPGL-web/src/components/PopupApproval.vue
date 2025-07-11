<!--PopupApporval.vue-->
<template>
  <div class="popup-panel" :class="{ show: isVisible }">
    <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">
      关闭
    </button>

    <h5>审批详情</h5>
    <div v-if="approval">
      <p><strong>审批ID: </strong> {{ approval.id }}</p>
      <p><strong>当前状态:</strong> {{ approval.status }}</p>
      <p><strong>发起仓库 / 商店:</strong> {{ approval.from }}</p>
      <p><strong>接收仓库 / 商店:</strong> {{ approval.to }}</p>
      <p><strong>商品编号:</strong> {{ approval.product || "未知" }}</p>
      <p><strong>商品数量:</strong> {{ approval.quantity || "未知" }}</p>
      <hr />

      <h6>时间记录</h6>
      <p><strong>申请发出时间:</strong> {{ approval.createdAt || "暂无" }}</p>
      <p><strong>审核时间:</strong> {{ approval.approvedAt || "暂无" }}</p>
      <p><strong>发货时间:</strong> {{ approval.shippedAt || "暂无" }}</p>
      <p><strong>收货时间:</strong> {{ approval.receivedAt || "暂无" }}</p>
    </div>
    <div v-else>
      <p>未选择审批项</p>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  approvalRequests: {
    type: Array,
    required: true,
  },
  selectedApprovalId: {
    type: String,
    default: null,
  },
});

const emit = defineEmits(["close"]);

const isVisible = ref(false);
const approval = ref(null);

watch(
  () => props.selectedApprovalId,
  (newId) => {
    if (newId) {
      approval.value =
        props.approvalRequests.find((a) => a.id === newId) || null;
      isVisible.value = true;
    } else {
      isVisible.value = false;
      approval.value = null;
    }
  }
);

const close = () => {
  isVisible.value = false;
  emit("close");
};

const show = (id) => {
  approval.value = props.approvalRequests.find((a) => a.id === id) || null;
  isVisible.value = true;
};

const relatedclose = () => {
  isVisible.value = false;
};

defineExpose({ show, relatedclose });
</script>

<style scoped>
@import "./popup-style.css";
</style>
