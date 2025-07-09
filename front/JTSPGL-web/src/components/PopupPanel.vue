<template>
  <div class="popup-panel" :class="{ show: isVisible }">
    <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">
      关闭
    </button>
    <div v-html="content"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const emit = defineEmits(['close']);

const isVisible = ref(false);
const content = ref('加载中...');

const stores = {
  WH001: ["北京王府井旗舰店", "武汉武商广场店"],
  WH002: ["上海徐家汇店", "南京新街口店", "杭州西湖店"],
  WH003: ["广州天河城店", "深圳万象城店"],
  WH004: ["成都春熙路店", "重庆解放碑店"],
  WH005: ["西安钟楼店"],
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
    status: "发货中",
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

const showWarehouseInfo = (id, name) => {
  let html = `<h5>${name} - 商店列表</h5>`;
  stores[id].forEach((store) => {
    html += `<button class='btn btn-sm btn-outline-secondary mb-3' onclick="this.dispatchEvent(new CustomEvent('store-click', { detail: '${store}', bubbles: true }))">${store}</button>`;
  });
  content.value = html;
  isVisible.value = true;
};

/*
似乎暂无作用
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
*/

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