<template>
  <div class="store-op-panel">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h4 class="mb-0"><strong>商店操作中心</strong></h4>
      <h5 class="mb-0">当前商店：{{ storeName }}</h5>
    </div>

    <div class="operations-grid">
      <!-- 商品信息查询 -->
      <div class="card">
        <div class="card-header">商品库存与销量</div>
        <div class="card-body d-flex align-items-center">
          <input
            v-model="queryInput"
            placeholder="商品ID或名称"
            class="form-control me-2"
            style="flex: 1"
          />
          <button class="btn btn-primary" @click="queryProduct">查询</button>
        </div>
        <div class="card-body" v-if="productResult">
          <pre>{{ productResult }}</pre>
        </div>
      </div>

      <!-- 调货 -->
      <div class="card">
        <div class="card-header">从仓库调货</div>
        <div class="card-body d-flex flex-wrap align-items-center gap-2">
          <input
            v-model="transferProduct"
            placeholder="商品ID"
            class="form-control"
            style="flex: 1"
          />
          <input
            v-model.number="transferQty"
            placeholder="数量"
            class="form-control"
            style="flex: 1"
          />
          <select
            v-model="selectedWarehouseId"
            class="form-select"
            style="flex: 1"
          >
            <option disabled value="">选择调出仓库</option>
            <option v-for="w in warehouseList" :key="w.id" :value="w.id">
              {{ w.name }}
            </option>
          </select>
          <button class="btn btn-primary" @click="transferIn">
            调货
          </button>
        </div>
      </div>

      <!-- 卖出商品 -->
      <div class="card">
        <div class="card-header">卖出商品</div>
        <div class="card-body d-flex align-items-center gap-2">
          <input
            v-model="sellProduct"
            placeholder="商品ID"
            class="form-control me-2"
            style="flex: 1"
          />
          <input
            v-model.number="sellQty"
            placeholder="数量"
            class="form-control me-2"
            style="flex: 1"
          />
          <button class="btn btn-primary" @click="sell">卖出</button>
        </div>
      </div>
      
      <!-- 销量预测 -->
      <div class="card">
        <div class="card-header">销量预测</div>
        <div class="card-body d-flex align-items-center gap-2">
          <input
            v-model="sellPredict"
            placeholder="商品ID"
            class="form-control me-2"
            style="flex: 1"
          />
          <button class="btn btn-primary" @click="predict">预测</button>
        </div>
        <div class="card-body" v-if="predictResult">
          <pre>{{ predictResult }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import axios from "axios";
import { showToast } from '@/utils/toast'

const emit = defineEmits(["new-approval", "addwarn"]);

// 当前商店信息（来自登录后本地存储）
const storeName = ref('');
const storeId = ref(localStorage.getItem("DetailInfo"));
const warehouseID = ref('');

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

// 预测字段
const sellPredict = ref("");
const predictResult = ref("");

onMounted(async () => {
  const res = await axios.get("http://localhost:5000/api/store/name", {
    params: {
      store_id: storeId.value,
    },
  });
  storeName.value = res.data.name;
});

// 查询商品
const queryProduct = async () => {
  const res = await axios.get("http://localhost:5000/api/store/products", {
    params: {
      store_id: storeId.value,
      query: queryInput.value,
    },
  });
  switch(res.data.successType){
    case 0:
      productResult.value = "查询失败：商品编号不存在";break;
    case 1:
      productResult.value = res.data.name + ": 未查询到销售记录\n商店库存量: " + res.data.inventory;break;
    case 2:
      productResult.value =
        res.data.name +
        " 单价:" +
        res.data.unit_price +
        " 销量:" +
        res.data.quantity +
        "\n商店库存量: " + res.data.store_inventory;
      break;
  }
};

// 调货逻辑
const transferIn = async () => {
  const fromWhName =
    warehouseList.value.find((w) => w.id === selectedWarehouseId.value)?.name ||
    "";
  const res = await axios.post("http://localhost:5000/api/request", {
    from_id: selectedWarehouseId.value,
    to_id: storeId.value,
    product_id: transferProduct.value,
    quantity: transferQty.value,
  });

  if (res.data.successType === 3) {
    emit("new-approval", {
      id: res.data.approval_id,
      product: transferProduct.value,
      quantity: transferQty.value,
      status: "待审核",
      from: selectedWarehouseId.value,
      to: storeId.value,
      request_time: new Date().toISOString(),
      approved_time: null,
      shipment_time: null,
      receipt_time: null,
      display: `${selectedWarehouseId.value}-${transferProduct.value}-${transferQty.value}-待审核`,
    });
    showToast("调货申请已提交", "success");
  }
};

// 卖出
const sell = async () => {
  const res = await axios.post("http://localhost:5000/api/store/sell", {
    store_id: storeId.value,
    product_id: sellProduct.value,
    quantity: sellQty.value,
  });
  switch(res.data.successType){
    case 0:alert("商品编号不存在");break;
    case 1:alert("请输入正整数");break;
    case 2:alert("仓库内商品库存不足");break;
    case 3:alert("卖出成功");break;
    case 4:alert(`卖出失败：${res.data.err}`);break;
    case 5:{
      alert("卖出成功，但库存量触发预警，系统自动发出调货申请。");

    };break;
  }
  if(res.data.successType == 5){
    emit("addwarn", 
      `商品${sellProduct.value}库存告警\n`
    );

    emit("new-approval", {
      id: res.data.approval_id,
      product: sellProduct.value,
      quantity: res.data.qty_num,
      status: "待审核",
      from: res.data.warehouse_id,
      to: storeName.value,
      request_time: new Date().toISOString(),
      approved_time: null,
      shipment_time: null,
      receipt_time: null,
      display: `${res.data.warehouse_id}-${sellProduct.value}-${res.data.qty_num}-待审核`,
    });
  }
};

// 预测
const predict = async () => {
  const res = await axios.post("http://localhost:5000/api/predict", {
    warehouse_id: storeId.value,
    product_id: sellPredict.value,
  });
  switch(res.data.successType){
    case 0: predictResult.value = "预测结果" + res.data.predict_sales;break;
    case 1: predictResult.value = "服务器错误";break;
    case 2: predictResult.value = "不存在相应商品编号";break;
    case 3: predictResult.value = "不存在相应销售记录";break;
  }
};
</script>

<style scoped>
.operations-grid {
  display: grid;
  grid-template-columns: 1fr 1fr; /* 两列 */
  grid-template-rows: auto auto; /* 两行 */
  gap: 1rem; /* 卡片间距 */
}

.card {
  height: 100%; /* 使卡片高度一致 */
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #ffffff, #f7f9fc);
  border: none;
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease-in-out;
}


.card-body {
  flex: 1; /* 使卡片内容区域填充剩余空间 */
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
}

.card-header {
  background: linear-gradient(to right, #518cea, #77b7f4);
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.store-op-panel {
  padding: 1px;
  background: linear-gradient(135deg, #c0d8f7, #f0f7ff);
  padding: 1rem;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}


.operations-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr); /* 两列自动适应 */
  gap: 1rem;
}

.card {
  height: 180px; /* 所有卡片统一高度 */
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}


</style>
