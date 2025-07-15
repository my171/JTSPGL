<!--PopupStore.vue-->
<template>
  <div class="popup-panel" :class="{ show: isVisible }">
    <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">
      关闭
    </button>
    <h5 v-if="storeName">商店：{{ storeName }}</h5>

    <hr />

    <!-- 商品信息查询 -->
    <h5>商品信息与销量</h5>
    <div class="input-group mb-2">
      <input
        class="form-control"
        v-model="queryInput"
        placeholder="输入商品ID"
      />
      <button class="btn btn-primary" @click="queryProduct">查询信息</button>
    </div>
    <div v-if="productResult">
      <pre>{{ productResult }}</pre>
    </div>

    <!-- 从仓库调货 -->
    <h5 class="mt-4">从仓库调货</h5>
    <div class="input-group mb-2">
      <input
        class="form-control"
        v-model="transferProduct"
        placeholder="商品ID"
      />
      <input class="form-control" v-model="transferQty" placeholder="数量" />
      <select class="form-select" v-model="selectedWarehouseId">
        <option disabled value="">选择调出仓库</option>
        <option v-for="wh in warehouseList" :key="wh.id" :value="wh.id">
          {{ wh.name }}
        </option>
      </select>
      <button class="btn btn-warning" @click="transferIn">调货</button>
    </div>

    <!-- 卖出商品 -->
    <h5 class="mt-4">卖出商品</h5>
    <div class="input-group mb-2">
      <input class="form-control" v-model="sellProduct" placeholder="商品ID" />
      <input class="form-control" v-model="sellQty" placeholder="数量" />
      <button class="btn btn-success" @click="sell">卖出</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";

const emit = defineEmits(["close"]);

const isVisible = ref(false);
const storeName = ref("");
const storeId = ref("");

const queryInput = ref("");
const productResult = ref("");

const transferProduct = ref("");
const transferQty = ref("");
const selectedWarehouseId = ref("");
const warehouseList = ref([]);

const sellProduct = ref("");
const sellQty = ref([]);
// 打开弹窗（传入商店 id 和 name）
const show = async (name, id) => {
  storeName.value = name;
  storeId.value = id;
  isVisible.value = true;

  // 加载仓库列表
  warehouseList.value = [
    { id: "WH001", name: "华北中心仓" },
    { id: "WH002", name: "华东智能仓" },
    { id: "WH003", name: "华南枢纽仓" },
    { id: "WH004", name: "西南分拨中心" },
    { id: "WH005", name: "东北冷链仓" },
  ];
};

// 查询商品信息
const queryProduct = async () => {
  try {
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
          "\n商店库存量: " + res.data.inventory;
        break;
    }
  } catch (err) {
    productResult.value = `查询失败：${err.message}`;
  }
};

// 从仓库调货
const transferIn = async () => {
  try {
    const fromWarehouseName =
      warehouseList.value.find((w) => w.id === selectedWarehouseId.value)
        ?.name || "";
    const response = await axios.post("http://localhost:5000/api/supply", {
      from_id: selectedWarehouse.value,
      to_id: storeId.value,
      product_id: transferProduct.value,
      quantity: Number(transferQty.value),
    });

    switch (response.data.successType) {
      case 0:
        alert("商品编号不存在");
        break;
      case 1:
        alert("仓库无相关商品记录");
        break;
      case 2:
        alert(
          "仓库内商品库存不足: 需求" +
            transferQty.value +
            " 储量" +
            response.data.num
        );
        break;
      case 3:
        alert("调货申请已提交");
        break;
      case 4:
        alert("调货失败：${err.message}");
        break;
    }
    if (response.data.successType == 3) {
      emit("new-approval", {
        id: data.approval_id,
        product: transferProduct.value,
        quantity: transferQty.value,
        status: "待审核",
        from: fromWarehouseName, //?????????????????????????
        //fromWarehouse is not defined
        to: storeName.value, //?????????????????????????
        //currentWarehouseName is not defined
        request_time: data.request_time,
        approved_time: null,
        shipment_time: null,
        receipt_time: null,
        // display 字段用于右侧面板按钮显示
        display: `${fromWarehouseName}-${transferProduct.value}-${transferQty.value}-待审核`,
      });
    }
  } catch (err) {
    alert(`调货失败：${err.message}`);
  }
};

// 卖出商品
const sell = async () => {
  try {
    const response = await axios.post("http://localhost:5000/api/store/sell", {
      store_id: storeId.value,
      product_id: sellProduct.value,
      quantity: Number(sellQty.value),
    });
    switch(response.data.successType){
      case 0:alert("商品编号不存在");break;
      case 1:alert("请输入正整数");break;
      case 2:alert("仓库内商品库存不足");break;
      case 3:alert("卖出成功");break;
      case 4:alert(`卖出失败：${response.data.err}`);break;
    }
  } catch (err) {
    alert(`卖出失败：${err.message}`);
  }
};

const close = () => {
  isVisible.value = false;
  emit("close");
};

const relatedclose = () => {
  isVisible.value = false;
};

defineExpose({ show, relatedclose });
</script>

<style scoped>

@import "./popup-style.css";
</style>
