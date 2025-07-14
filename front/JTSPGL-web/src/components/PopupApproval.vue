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
      <p><strong>发货仓库:</strong> {{ approval.from }}</p>
      <p><strong>接收仓库 / 商店:</strong> {{ approval.to }}</p>
      <p><strong>商品编号:</strong> {{ approval.product || "未知" }}</p>
      <p><strong>商品数量:</strong> {{ approval.quantity || "未知" }}</p>
      <hr />

      <h6>时间记录</h6>
      <p><strong>申请发出时间:</strong> {{ approval.createdAt || "暂无" }}</p>
      <p><strong>审核时间:</strong> {{ approval.approvedAt || "暂无" }}</p>
      <p><strong>发货时间:</strong> {{ approval.shippedAt || "暂无" }}</p>
      <p><strong>收货时间:</strong> {{ approval.receivedAt || "暂无" }}</p>
      <hr />
      <!-- 动作按钮 -->
      <div class="mt-3">
        <button
          v-if="approval.status === '待审核'"
          class="btn btn-success me-2"
          @click="approve(true)"
        >
          审核通过
        </button>
        <button
          v-if="approval.status === '待审核'"
          class="btn btn-danger"
          @click="approve(false)"
        >
          审核不通过
        </button>

        <button
          v-if="approval.status === '待出库'"
          class="btn btn-warning me-2"
          @click="ship"
        >
          发货
        </button>
        <button
          v-if="approval.status === '待收货'"
          class="btn btn-primary"
          @click="receive"
        >
          收货
        </button>
      </div>
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

// 状态变化函数
const getNow = () => new Date().toLocaleString();

const approve = (passed) => {
  if (!approval.value) return;
  approval.value.status = passed ? "待出库" : "已取消";
  approval.value.approvedAt = getNow();
  approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;
};

const ship = () => {
  if (!approval.value) return;
  approval.value.status = "待收货";
  approval.value.shippedAt = getNow();
  approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;
};

const receive = () => {
  if (!approval.value) return;
  approval.value.status = "已完成";
  approval.value.receivedAt = getNow();
  approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;
};

defineExpose({ show, relatedclose });
</script>

<style scoped>
@import "./popup-style.css";
</style>
