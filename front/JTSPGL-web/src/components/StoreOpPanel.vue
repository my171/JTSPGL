<!--StoreOpPanel.vue-->
//商店用户的主操作界面
<!-- StoreOpPanel.vue -->
<template>
    <div class="store-op-panel">
      <h4>商店操作中心</h4>
      <p><strong>当前商店：</strong>{{ storeName }}</p>
  
      <!-- 商品信息查询 -->
      <div class="card mb-3">
        <div class="card-header">商品信息与销量</div>
        <div class="card-body">
          <input v-model="queryInput" placeholder="商品ID或名称" class="form-control mb-2" />
          <button class="btn btn-primary" @click="queryProduct">查询信息</button>
          <pre v-if="productResult">{{ productResult }}</pre>
        </div>
      </div>
  
      <!-- 调货 -->
      <div class="card mb-3">
        <div class="card-header">从仓库调货</div>
        <div class="card-body">
          <input v-model="transferProduct" placeholder="商品ID" class="form-control mb-2" />
          <input v-model.number="transferQty" placeholder="数量" class="form-control mb-2" />
          <select v-model="selectedWarehouseId" class="form-select mb-2">
            <option disabled value="">选择调出仓库</option>
            <option v-for="w in warehouseList" :key="w.id" :value="w.id">{{ w.name }}</option>
          </select>
          <button class="btn btn-warning" @click="transferIn">调货</button>
        </div>
      </div>
  
      <!-- 卖出商品 -->
      <div class="card mb-3">
        <div class="card-header">卖出商品</div>
        <div class="card-body">
          <input v-model="sellProduct" placeholder="商品ID" class="form-control mb-2" />
          <input v-model.number="sellQty" placeholder="数量" class="form-control mb-2" />
          <button class="btn btn-success" @click="sell">卖出</button>
        </div>
      </div>
    </div>
  </template>
  
  <script setup>
  import { ref } from "vue";
  import axios from "axios";
  
  const emit = defineEmits(["new-approval"]);
  
  // 当前商店信息（来自登录后本地存储）
  const storeName = ref(localStorage.getItem("store_name"));
  const storeId = ref(localStorage.getItem("store_id"));
  
  // 商品查询
  const queryInput = ref("");
  const productResult = ref("");
  
  // 调货字段
  const transferProduct = ref("");
  const transferQty = ref(0);
  const selectedWarehouseId = ref("");
  const warehouseList = ref([
    { id: "WH001", name: "华北中心仓" },
    { id: "WH002", name: "华东智能仓" },
    { id: "WH003", name: "华南枢纽仓" },
    { id: "WH004", name: "西南分拨中心" },
    { id: "WH005", name: "东北冷链仓" },
  ]);
  
  // 卖出字段
  const sellProduct = ref("");
  const sellQty = ref(0);
  
  // 查询商品
  const queryProduct = async () => {
    const res = await axios.get("http://localhost:5000/api/store/products", {
      params: {
        storeId: storeId.value,
        productId: queryInput.value,
      },
    });
    productResult.value = res.data.name ? `单价:${res.data.unit_price}, 销量:${res.data.quantity}` : "无记录";
  };
  
  // 调货逻辑
  const transferIn = async () => {
    const fromWhName = warehouseList.value.find(w => w.id === selectedWarehouseId.value)?.name || "";
    const res = await axios.post("http://localhost:5000/api/supply", {
      fromWarehouseID: selectedWarehouseId.value,
      store_id: storeId.value,
      product_id: transferProduct.value,
      quantity: transferQty.value,
    });
  
    if (res.data.successType === 3) {
      emit("new-approval", {
        id: Math.random().toString(36).substring(2, 9),
        product: transferProduct.value,
        quantity: transferQty.value,
        status: "待审核",
        from: fromWhName,
        to: storeName.value,
        request_time: new Date().toISOString(),
        display: `${fromWhName}-${transferProduct.value}-${transferQty.value}-待审核`,
      });
      alert("调货申请已提交");
    }
  };
  
  // 卖出
  const sell = async () => {
    const res = await axios.post("http://localhost:5000/api/store/sell", {
      store_id: storeId.value,
      product_id: sellProduct.value,
      quantity: sellQty.value,
    });
    alert(res.data.successType === 3 ? "卖出成功" : "库存不足");
  };
  </script>
  
  <style scoped>
  .store-op-panel {
    padding: 20px;
  }
  .card {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  </style>