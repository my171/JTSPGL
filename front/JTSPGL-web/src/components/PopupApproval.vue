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
      <p>
        <strong>申请发出时间:</strong> {{ approval.request_time || "暂无" }}
      </p>
      <p><strong>审核时间:</strong> {{ approval.approved_time || "暂无" }}</p>
      <p><strong>发货时间:</strong> {{ approval.shipment_time || "暂无" }}</p>
      <p><strong>收货时间:</strong> {{ approval.receipt_time || "暂无" }}</p>
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
        <button
          v-if="canCancel"
          class="btn btn-outline-danger mt-3"
          @click="cancelApproval"
        >
          取消申请
        </button>
      </div>
    </div>

    <div v-else>
      <p>未选择审批项</p>
    </div>
  </div>
</template>

<script setup>
import axios from "axios";
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

// 权限控制
const userRole = localStorage.getItem("user_role");
const warehouseName = localStorage.getItem("warehouse_name");
const storeName = localStorage.getItem("store_name");

const canCancel = ref(false);

watch(
  () => props.selectedApprovalId,
  (newId) => {
    if (!newId) {
      isVisible.value = false;
      approval.value = null;
      return;
    }

    approval.value = props.approvalRequests.find((a) => a.id === newId) || null;
    isVisible.value = true;

    // 判断是否可取消
    const isCreator =
      approval.value.from === warehouseName ||
      approval.value.from === storeName;

    canCancel.value =
      ["待审核", "待出库"].includes(approval.value?.status) &&
      (userRole === "admin" ||
        (isCreator && (userRole === "warehouse" || userRole === "store")));
  }
);
const cancelApproval = async () => {
  if (!approval.value) return;

  if (!confirm(`确定要取消此调货申请吗？\n状态将变为“已取消”。`)) return;

  try {
    await axios.post("http://localhost:5000/api/approval/cancel", {
      approval_id: approval.value.id,
      canceled_by:
        localStorage.getItem("warehouse_name") ||
        localStorage.getItem("store_name"),
    });

    approval.value.status = "已取消";
    approval.value.canceled_time = new Date().toISOString();
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-已取消`;

    emit("update-approval", approval.value);
    alert("调货申请已取消");
  } catch (err) {
    alert("取消失败：" + err.message);
  }
};
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

//APPROVAL BUTTONS
const approve = async (passed) => {
  if (!approval.value) return;
  try {
    const url = passed
      ? `http://localhost:5000/api/approval/accepted`
      : `http://localhost:5000/api/approval/rejected`;

    const response = axios.post(url, {
      approval_id: approval.value.id,
    });

    const { approvedAt } = response.data;

    approval.value.status = passed ? "待出库" : "已取消";
    approval.value.approvedAt = approvedAt;
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;

    emit("update-approval", approval.value);
  } catch (err) {
    alert(`操作失败：${err.message}`);
  }
};

//SHIP BUTTON
const ship = async () => {
  if (!approval.value) return;
  try {
    const response = await axios.post("http://localhost:5000/api/shipment", {
      approval_id: approval.value.id,
    });

    const { shippedAt } = response.data;

    approval.value.status = "待收货";
    approval.value.shippedAt = shippedAt;
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;

    emit("update-approval", approval.value);
  } catch (err) {
    alert(`发货失败：${err.message}`);
  }
};

//RECEIVE BUTTON
const receive = async () => {
  if (!approval.value) return;
  try {
    const response = await axios.post("http://localhost:5000/api/shipment", {
      approval_id: approval.value.id,
    });

    const { receivedAt } = response.data;

    approval.value.status = "已完成";
    approval.value.receivedAt = receivedAt;
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;

    emit("update-approval", approval.value);
  } catch (err) {
    alert(`收货失败：${err.message}`);
  }
};

defineExpose({ show, relatedclose });
</script>

<style scoped>
.popup-panel {
  position: fixed;
  top: 50px;
  right: 0;
  width: 400px;
  background-color: #fff;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: transform 0.3s ease;
  z-index: 1000;
}
.popup-panel.show {
  transform: translateX(0);
}
</style>
