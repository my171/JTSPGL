<template>
  <div class="col-md-3 right-panel" :style="{ transform: panelTransform }">
    <h5>AI 实时预警</h5>
    <textarea class="form-control mb-3" rows="3" readonly>暂无预警</textarea>

    <h5 class="mt-4">审批流进度</h5>

    <div v-if="approvalRequests.length === 0">暂无审批流记录</div>

    <div v-for="(group, status) in groupedApprovals" :key="status">
      <h6 class="mt-3">{{ status }}</h6>
      <button
        v-for="item in group"
        :key="item.id"
        class="approval-button"
        :class="`status-${statusColorMap[item.status] || 'gray'}`"
        @click="showApproval(item.id)"
      >
        {{ item.display }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const emit = defineEmits(["show-approval"]);

const props = defineProps({
  approvalRequests: {
    type: Array,
    required: true,
  },
});

const panelTransform = ref("translateX(0)");

const statusColorMap = {
  待审核: "gray",
  审核不通过: "red",
  待出库: "yellow",
  待收货: "yellow",
  已完成: "green",
};

const groupedApprovals = computed(() => {
  const groups = {};
  for (const item of props.approvalRequests) {
    if (!groups[item.status]) {
      groups[item.status] = [];
    }
    groups[item.status].push(item);
  }
  return groups;
});

const showApproval = (id) => {
  emit("show-approval", id);
};

const movePanel = () => {
  panelTransform.value = "translateX(-200px)";
};

const resetPanel = () => {
  panelTransform.value = "translateX(0)";
};

defineExpose({
  movePanel,
  resetPanel,
});
</script>

<style scoped>
.right-panel {
  height: 100vh;
  background-color: #ffffff;
  border-left: 1px solid #ddd;
  padding: 20px;
  overflow-y: auto;
  transition: transform 0.3s ease-in-out;
}

.approval-button {
  width: 100%;
  text-align: left;
  display: inline-block;
  padding: 6px 12px;
  margin: 5px 0;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  font-size: 14px;
  transition: 0.2s;
}

.status-gray {
  background-color: #e0e0e0;
  color: #333;
  border: 1px solid #bcbbbb;
  transition: transform 0.1s ease;
}

.status-gray:hover {
  background-color: #bcbbbb;
  color: #333;
  transform: scale(1.02);
}

.status-red {
  background-color: #ff9090;
  color: #842029;
  border: 1px solid #f8c4c9;
  transition: transform 0.1s ease;
}

.status-red:hover {
  background-color: #f65c5c;
  color: #842029;
  transform: scale(1.02);
}

.status-yellow {
  background-color: #fff3cd;
  color: #664d03;
  border: 1px solid #f8e6a8;
  transition: transform 0.1s ease;
}

.status-yellow:hover {
  background-color: #f8e6a8;
  color: #664d03;
  transform: scale(1.02);
}

.status-green {
  background-color: rgb(174, 238, 174);
  color: #0f5132;
  border: 1px solid #bfffbf;
  transition: transform 0.1s ease;
}

.status-green:hover {
  background-color: rgb(157, 240, 157);
  color: #0f5132;
  transform: scale(1.02);
}
</style>
