<!--PopupApporval.vue-->
<template>
  <div class="popup-panel" :class="{ show: isVisible }">
    <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">
      关闭
    </button>

    <div class="popup-content">
    <div v-if="approval">
      <h5>审批详情</h5>
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
          @click="approveAccepted"
        >
          审核通过
        </button>
        <button
          v-if="approval.status === '待审核'"
          class="btn btn-danger"
          @click="approveRejected"
        >
          审核不通过
        </button>

        <button
          v-if="approval.status === '待发货'"
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
      ["待审核", "待发货"].includes(approval.value?.status) &&
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
const approveAccepted = async () => {
  if (!approval.value) return;

  try {
    const response = await axios.post("http://localhost:5000/api/approval/accepted", {
      approval_id: approval.value.id,
    });

    const { approval_time: approvedAt } = response.data;

    approval.value.status = "待发货";
    approval.value.approvedAt = approvedAt;
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-待发货`;

    emit("update-approval", approval.value);
  } catch (err) {
    alert(`审核通过失败：${err.message}`);
  }
};

const approveRejected = async () => {
  if (!approval.value) return;

  try {
    const response = await axios.post("http://localhost:5000/api/approval/rejected", {
      approval_id: approval.value.id,
    });

    const { approval_time: approvedAt } = response.data;

    approval.value.status = "已取消";
    approval.value.approvedAt = approvedAt;
    approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-已取消`;

    emit("update-approval", approval.value);
  } catch (err) {
    alert(`审核拒绝失败：${err.message}`);
  }
};
//SHIP BUTTON
const ship = async () => {
  if (!approval.value) return;
  try {
    const response = await axios.post("http://localhost:5000/api/shipment", {
      approval_id: approval.value.id,
    });
    switch(response.data.successType){
      case 0:{
        const { shippedAt } = response.data;

        approval.value.status = "待收货";
        approval.value.shippedAt = shippedAt;
        approval.value.display = `${approval.value.from}-${approval.value.product}-${approval.value.quantity}-${approval.value.status}`;

        emit("update-approval", approval.value);
        break;
      }
      case 1:{
        alert("发货失败：商品不足");
        break;
      }
      case 2:{
        alert("发货失败：" + response.data.err);
      }
    }
  } catch (err) {
    alert(`发货失败：${err.message}`);
  }
};

//RECEIVE BUTTON
const receive = async () => {
  if (!approval.value) return;
  try {
    const response = await axios.post((approval.value.to.startsWith("WH"))?"http://localhost:5000/api/receipt/warehouse" : "http://localhost:5000/api/receipt/store", {
      approval_id: approval.value.id,
    });

    const { receivedAt } = response.data;

    approval.value.status = "已收货";
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
@import "./popup-style.css";
/* popup-style.css */
.popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 999;
}

.popup-panel.show {
  right: 0; /* 弹出到屏幕右侧 */
}

.popup-overlay.show .popup-mask {
  background-color: rgba(0, 0, 0, 0.4);
  visibility: visible;
  opacity: 1;
}
</style>
