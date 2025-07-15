<!--WarehouseOpPanel.vue-->
//仓库用户的主操作界面
<!-- WarehouseOpPanel.vue -->
<template>
  <div class="warehouse-op-panel">
    <h4>仓库操作中心</h4>

    <!-- 商品库存查询 -->
    <div class="card mb-3">
      <div class="card-header">商品库存查询</div>
      <div class="card-body">
        <div class="input-group mb-2">
          <input v-model="queryInput" placeholder="输入商品ID" class="form-control" />
          <button class="btn btn-primary" @click="queryProduct">查询</button>
        </div>
        <pre v-if="productResult">{{ productResult }}</pre>
      </div>
    </div>

    <!-- 补货操作 -->
    <div class="card mb-3">
      <div class="card-header">补货操作</div>
      <div class="card-body position-relative">
        <div class="mb-2">
          <input v-model="replenishProduct" placeholder="商品ID" class="form-control" />
        </div>
        <div class="mb-2">
          <input v-model.number="replenishQty" placeholder="补货数量" class="form-control" />
        </div>
        <button class="btn btn-success position-absolute" style="top: 50%; right: 10px; transform: translateY(-50%);" @click="replenish">
          补货
        </button>
      </div>
    </div>

    <!-- 调货操作 -->
    <div class="card mb-3">
      <div class="card-header">调货申请</div>
      <div class="card-body position-relative">
        <div class="mb-2">
          <input v-model="transferProduct" placeholder="商品ID" class="form-control" />
        </div>
        <div class="mb-2">
          <input v-model.number="transferQty" placeholder="调货数量" class="form-control" />
        </div>
        <div class="mb-2">
          <select v-model="selectedWarehouse" class="form-select">
            <option disabled value="">选择目标仓库</option>
            <option v-for="w in warehouseList" :key="w.id" :value="w.id">{{ w.name }}</option>
          </select>
        </div>
        <button class="btn btn-warning position-absolute" style="top: 50%; right: 10px; transform: translateY(-50%);" @click="transfer">
          提交调货
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";

const emit = defineEmits(["new-approval"]);

// 数据字段
const queryInput = ref("");
const productResult = ref("");

const replenishProduct = ref("");
const replenishQty = ref(0);

const transferProduct = ref("");
const transferQty = ref(0);
const selectedWarehouse = ref("");
const warehouseList = ref([
  { id: "WH001", name: "华北中心仓" },
  { id: "WH002", name: "华东智能仓" },
  { id: "WH003", name: "华南枢纽仓" },
  { id: "WH004", name: "西南分拨中心" },
  { id: "WH005", name: "东北冷链仓" },
]);

// 查询库存
const queryProduct = async () => {
  try {
    const res = await axios.get(
      "http://localhost:5000/api/warehouses/products",
      {
        params: {
          warehouseId: localStorage.getItem("warehouse_id"), // 假设已知当前仓库id
          productId: queryInput.value,
        },
      }
    );
    productResult.value = `${res.data.name}: 库存${res.data.quantity}`;
  } catch (err) {
    productResult.value = "查询失败：" + err.message;
  }
};

// 补货
const replenish = async () => {
  try {
    const res = await axios.post("http://localhost:5000/api/replenish", {
      warehouse_id: localStorage.getItem("warehouse_id"),
      product: replenishProduct.value,
      quantity: replenishQty.value,
    });
    alert("补货成功");
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
    fromWarehouseID: localStorage.getItem("warehouse_id"),
    warehouse_id: selectedWarehouse.value,
    product_id: transferProduct.value,
    quantity: transferQty.value,
  });

  if (res.data.successType === 3) {
    emit("new-approval", {
      id: res.data.approval_id,
      product: transferProduct.value,
      quantity: transferQty.value,
      status: "待审核",
      from: localStorage.getItem("warehouse_name"),
      to: toWarehouse,
      request_time: new Date().toISOString(),
      display: `${localStorage.getItem("warehouse_name")}-${
        transferProduct.value
      }-${transferQty.value}-待审核`,
    });
    alert("调货申请已提交");
  }
};
</script>

<style scoped>
.warehouse-op-panel {
  padding: 20px;
}
.card {
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
</style>
