<!--WarehouseOpPanel.vue-->
<template>
  <div class="warehouse-op-panel">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h4 class="mb-0"><strong>仓库操作中心</strong></h4>
      <h5 class="mb-0">当前仓库：{{ warehouseName }}</h5>
    </div>

    <div class="operations-grid">
      <!-- 商品库存查询 -->
      <div class="card mb-3">
        <div class="card-header">商品库存查询</div>
        <div class="card-body d-flex align-items-center">
          <input
            v-model="queryInput"
            placeholder="输入商品ID"
            class="form-control me-2"
            style="flex: 1"
          />
          <button class="btn btn-primary" @click="queryProduct">查询</button>
        </div>
        <div class="card-body" v-if="productResult">
          <pre>{{ productResult }}</pre>
        </div>
      </div>
      <!-- 补货操作 -->
      <div class="card mb-3">
        <div class="card-header">补货操作</div>
        <div class="card-body d-flex align-items-center gap-2">
          <input
            v-model="replenishProduct"
            placeholder="商品ID"
            class="form-control me-2"
            style="flex: 1"
          />
          <input
            v-model.number="replenishQty"
            placeholder="补货数量"
            class="form-control me-2"
            style="flex: 1"
          />
          <button class="btn btn-success" @click="replenish">补货</button>
        </div>
      </div>
      <!-- 调货操作 -->
      <div class="card mb-3">
        <div class="card-header">调货申请</div>
        <div class="card-body position-relative" style="padding-right: 80px">
          <!-- 商品ID -->
          <div class="mb-2" style="max-width: 1080px">
            <input
              v-model="transferProduct"
              placeholder="商品ID"
              class="form-control"
            />
          </div>

          <!-- 调货数量 -->
          <div class="mb-2" style="max-width: 1080px">
            <input
              v-model.number="transferQty"
              placeholder="调货数量"
              class="form-control"
            />
          </div>

          <!-- 目标仓库 -->
          <div class="mb-2" style="max-width: 1080px">
            <select v-model="selectedWarehouse" class="form-select">
              <option disabled value="">选择目标仓库</option>
              <option v-for="w in warehouseList" :key="w.id" :value="w.id">
                {{ w.name }}
              </option>
            </select>
          </div>

          <!-- 提交按钮 -->
          <button
            class="btn btn-warning position-absolute translate-middle-y"
            @click="transfer"
            style="top: 50%; right: 15px; transform: translateY(-50%); z-index: 2"
          >
            调货
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { showToast } from '@/utils/toast'

const emit = defineEmits(["new-approval"]);

// 数据字段

const warehouseList = ref([
  { id: "WH001", name: "华北中心仓" },
  { id: "WH002", name: "华东智能仓" },
  { id: "WH003", name: "华南枢纽仓" },
  { id: "WH004", name: "西南分拨中心" },
  { id: "WH005", name: "东北冷链仓" },
]);

const warehouseId = ref(localStorage.getItem("DetailInfo"));
const warehouseName = ref("");

const queryInput = ref("");
const productResult = ref("");

const replenishProduct = ref("");
const replenishQty = ref(0);

const transferProduct = ref("");
const transferQty = ref(0);
const selectedWarehouse = ref("");

onMounted(() => {
  const warehouse = warehouseList.value.find(item => item.id === warehouseId.value);
  if (warehouse) {
    warehouseName.value = warehouse.name;
  }
});

// 查询库存
const queryProduct = async () => {
  try {
    const res = await axios.get(
      `http://localhost:5000/api/warehouses/${warehouseId.value}/products`,
      {
        params: {
          query: queryInput.value,
        },
      }
    );
    switch (res.data.successType){
      case 0:
        productResult.value = "查询失败: 商品编号不存在";
        break;
      case 1:
        productResult.value = res.data.name + ":暂无库存";
        break;
      case 2:
        productResult.value = res.data.name + ":库存量" + res.data.quantity;
        break;
      case 3:
        productResult.value = "查询失败: 信息未输入"
        break;
    }
  } catch (err) {
    productResult.value = "查询失败：" + err.message;
  }
};

// 补货
const replenish = async () => {
  try {
    const response = await axios.post("http://localhost:5000/api/replenish", {
      warehouse_id: warehouseId.value,
      product: replenishProduct.value,
      quantity: replenishQty.value,
    });
    switch (response.data.successType) {
      case 0:
        alert("补货失败: 未知商品编号");
        break;
      case 1:
        alert("补货成功");
        break;
      case 2:
        alert(`补货失败：${response.data.err}`);
        break;
      case 3:
        alert("商品数量输入有误");
        break;
    }
  } catch (err) {
    alert("补货失败：" + err.message);
  }
};

// 调货
const transfer = async () => {
  const toWarehouse =
    warehouseList.value.find((w) => w.id === selectedWarehouse.value)?.name ||
    "";
  const res = await axios.post("http://localhost:5000/api/request", {
    from_id: selectedWarehouse.value,
    to_id: warehouseId.value,
    product_id: transferProduct.value,
    quantity: transferQty.value,
  });

  if (res.data.successType === 3) {
    emit("new-approval", {
      id: res.data.approval_id,
      product: transferProduct.value,
      quantity: transferQty.value,
      status: "待审核",
      from: localStorage.getItem("DetailInfo"),
      to: toWarehouse,
      request_time: new Date().toISOString(),
      display: `${localStorage.getItem("DetailInfo")}-${
        transferProduct.value
      }-${transferQty.value}-待审核`,
    });
    alert("调货申请已提交");
  }
};
</script>

<style scoped>
.operations-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr; /* 两列 */
  grid-template-rows: auto auto; /* 两行 */
  gap: 1rem; /* 卡片间距 */
}

.warehouse-op-panel {
  padding: 20px;
}
.card {
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
</style>
