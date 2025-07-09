<template>
  <div class="popup-panel" :class="{ show: isVisible }">
    <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">关闭</button>

    <!-- 商店按钮区域 -->
    <div v-html="content" @store-click="handleStoreClick"></div>

    <hr />

    <!-- 商品信息查询 -->
    <h5>商品信息查询</h5>
    <div class="input-group mb-2">
      <input class="form-control" v-model="queryInput" placeholder="输入商品ID或名称" />
      <button class="btn btn-primary" @click="queryProductInfo">查询信息</button>
      <button class="btn btn-info" @click="querySalesHistory">查询往期销量</button>
    </div>
    <div v-if="productResult">
      <pre>{{ productResult }}</pre>
    </div>

    <!-- 补货 -->
    <h5 class="mt-4">补货操作</h5>
    <div class="input-group mb-2">
      <input class="form-control" v-model="replenishProduct" placeholder="商品名称或ID" />
      <input class="form-control" v-model="replenishQty" placeholder="补货数量" />
      <button class="btn btn-success" @click="replenish">补货</button>
    </div>

    <!-- 调货 -->
    <h5 class="mt-4">调货操作</h5>
    <div class="input-group mb-2">
      <input class="form-control" v-model="transferProduct" placeholder="商品名称或ID" />
      <input class="form-control" v-model="transferQty" placeholder="调货数量" />
      <select class="form-select" v-model="selectedWarehouse">
        <option disabled value="">选择调出仓库</option>
        <option v-for="wh in warehouseList" :key="wh.id" :value="wh.id">{{ wh.name }}</option>
      </select>
      <button class="btn btn-warning" @click="transfer">调货</button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const emit = defineEmits(['close']);

const isVisible = ref(false);
const content = ref('加载中...');

const showWarehouseInfo = async (id, name) => {
  content.value = `<h5>${name} - 商店列表</h5><p>加载中...</p>`;
  isVisible.value = true;

  try {
    //调用后端接口加载该仓库的商店列表
    const response = await axios.get(`http://localhost:5000/api/warehouses/${id}/stores`);
    const storeList = response.data; // 返回格式 ["上海徐家汇店", "广州天河城店"]

    //动态生成按钮
    let html = `<h5>${name} - 商店列表</h5>`;
    storeList.forEach((store) => {
      html += `<button class='btn btn-sm btn-outline-secondary mb-3' onclick="this.dispatchEvent(new CustomEvent('store-click', { detail: '${store}', bubbles: true }))">${store}</button>`;
    });
    content.value = html;

  } catch (err) {
    content.value = `<p class="text-danger">加载失败：${err.message}</p>`;
  }
};


const infoMap = {
  P10001: {
    status: "待审核",
    decisionTime: "-",
    reviewTime: "-",
    dispatchTime: "-",
    receivedTime: "-",
    from: "华东智能仓",
    to: "南京新街口店",
  },
  P10006: {
    status: "已完成",
    decisionTime: "2025-07-01 10:00",
    reviewTime: "2025-07-02 11:00",
    dispatchTime: "2025-07-03 15:30",
    receivedTime: "2025-07-05 09:15",
    from: "华北中心仓",
    to: "北京王府井旗舰店",
  },
  P10002: {
    status: "审核不通过",
    decisionTime: "2025-06-28 14:00",
    reviewTime: "2025-06-29 09:30",
    dispatchTime: "-",
    receivedTime: "-",
    from: "华南枢纽仓",
    to: "广州天河城店",
  },
  P10003: {
    status: "待出库",
    decisionTime: "2025-06-30 08:00",
    reviewTime: "-",
    dispatchTime: "-",
    receivedTime: "-",
    from: "西南分拨中心",
    to: "成都春熙路店",
  },
  P10004: {
    status: "待收货",
    decisionTime: "2025-07-01 12:00",
    reviewTime: "2025-07-01 13:30",
    dispatchTime: "2025-07-02 10:00",
    receivedTime: "-",
    from: "东北冷链仓",
    to: "西安钟楼店",
  },
  P10005: {
    status: "待收货",
    decisionTime: "2025-07-02 16:00",
    reviewTime: "2025-07-03 09:00",
    dispatchTime: "2025-07-04 14:30",
    receivedTime: "-",
    from: "华东智能仓",
    to: "上海徐家汇店",
  },
};



const showStoreOptions = (store) => {
  let html = `<h5>${store} - 操作选项</h5>
    <div class='query-options'>
      <div class="input-group mb-3">
        <input class="form-control" placeholder="输入商品编号或名称">
        <button class="btn btn-primary">查询</button>
      </div>
      <div class="input-group">
        <input class="form-control" placeholder="输入商品编号或名称">
        <button class="btn btn-success">调货</button>
      </div>
    </div>`;
  content.value = html;
};


const showApprovalDetail = (productId) => {
  const item = infoMap[productId] || {
    status: "未知",
    decisionTime: "-",
    reviewTime: "-",
    dispatchTime: "-",
    receivedTime: "-",
    from: "-",
    to: "-",
  };
  
  const html = `
    <h5>审批详情：${productId}</h5>
    <p><strong>当前状态：</strong>${item.status}</p>
    <p><strong>调出仓库：</strong>${item.from}</p>
    <p><strong>调入商店：</strong>${item.to}</p>
    <p><strong>决策时间：</strong>${item.decisionTime}</p>
    <p><strong>审核时间：</strong>${item.reviewTime}</p>
    <p><strong>发货时间：</strong>${item.dispatchTime}</p>
    <p><strong>收货时间：</strong>${item.receivedTime}</p>
  `;
  content.value = html;
  isVisible.value = true;
};

const close = () => {
  isVisible.value = false;
  emit('close');
};

defineExpose({
  showWarehouseInfo,
  showApprovalDetail
});
</script>

<style scoped>
.popup-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 400px;
  height: 100vh;
  background: #fff;
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
  overflow-y: auto;
  z-index: 9999;
  transform: translateX(100%);
  transition: transform 0.3s ease-in-out;
}

.popup-panel.show {
  transform: translateX(0);
}
.store-button {
  width: 100%;
  text-align: left;
  display: inline-block;
  padding: 6px 12px;
  margin: 5px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  font-size: 14px;
  transition: 0.2s;
}
/*
.store-button {
  display: inline-block;
  padding: 6px 12px;
  margin: 5px;
  border-radius: 8px;
  cursor: pointer;
  border: none;
  font-size: 14px;
  transition: 0.2s;
  background-color: #f8f9fa;
  border: 1px solid #ccc;
}
  */

.store-button:hover {
  background-color: #e2e6ea;
}

.query-options {
  margin-top: 15px;
}
</style>