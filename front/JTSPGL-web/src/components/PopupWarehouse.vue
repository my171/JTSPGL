<!-- PopupWarehouse.vue -->
<template>
    <div class="popup-panel" :class="{ show: isVisible }">
      <button class="btn btn-sm btn-outline-secondary mb-3" @click="close">关闭</button>
      <div v-html="content" @store-click="handleStoreClick"></div>
  
      <hr />
  
      <!-- 商品信息查询 -->
      <h5>商品信息查询</h5>
      <div class="input-group mb-2">
        <input class="form-control" v-model="queryInput" placeholder="输入商品ID或名称" />
        <button class="btn btn-primary" @click="queryProductInfo">查询信息</button>
      </div>
      <div v-if="productResult">
        <pre>{{ productResult }}</pre>
      </div>
  
      <!-- 补货 -->
      <h5 class="mt-4">补货操作</h5>
      <div class="input-group mb-2">
        <input class="form-control" v-model="replenishProduct" placeholder="商品ID" />
        <input class="form-control" v-model="replenishQty" placeholder="补货数量" />
        <button class="btn btn-success" @click="replenish">补货</button>
      </div>
  
      <!-- 调货 -->
      <h5 class="mt-4">调货申请</h5>
      <div class="input-group mb-2">
        <input class="form-control" v-model="transferProduct" placeholder="商品ID" />
        <input class="form-control" v-model="transferQty" placeholder="调货数量" />
        <select class="form-select" v-model="selectedWarehouse">
          <option disabled value="">调出仓库</option>
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
  
  // 查询 & 操作表单
  const queryInput = ref('');
  const productResult = ref('');
  
  const replenishProduct = ref('');
  const replenishQty = ref('');
  
  const transferProduct = ref('');
  const transferQty = ref('');
  const selectedWarehouse = ref('');


    const show = async (id, name) => {
    content.value = `<h5>${name} - 商店列表</h5><p>加载中...</p>`;
    isVisible.value = true;
  
    try {
      const response = await axios.get(`http://localhost:5000/api/warehouses/${id}/stores`);
      const storeList = response.data;
      let html = `<h5>${name} - 商店列表</h5>`;
      storeList.forEach((store) => {
        html += `<button class='btn btn-sm btn-outline-secondary mb-3' onclick="this.dispatchEvent(new CustomEvent('store-click', { detail: '${store}', bubbles: true }))">${store}</button>`;
      });
      content.value = html;
    } catch (err) {
      content.value = `<p class="text-danger">加载失败：${err.message}</p>`;
    }
  };


  const handleStoreClick = (e) => {
    const storeName = e.detail;
    alert(`点击了商店：${storeName}`);
  };
  
  
  const queryProductInfo = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/product/info', {
        params: { query: queryInput.value }
      });
      productResult.value = JSON.stringify(res.data, null, 2);
    } catch (err) {
      productResult.value = `查询失败：${err.message}`;
    }
  };
  
  const querySalesHistory = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/product/history', {
        params: { query: queryInput.value }
      });
      productResult.value = JSON.stringify(res.data, null, 2);
    } catch (err) {
      productResult.value = `查询失败：${err.message}`;
    }
  };
  
  const replenish = async () => {
    try {
      await axios.post('http://localhost:5000/api/replenish', {
        product: replenishProduct.value,
        quantity: Number(replenishQty.value)
      });
      alert('补货成功');
    } catch (err) {
      alert(`补货失败：${err.message}`);
    }
  };
  
  const transfer = async () => {
    try {
      await axios.post('http://localhost:5000/api/transfer', {
        product: transferProduct.value,
        quantity: Number(transferQty.value),
        fromWarehouse: selectedWarehouse.value
      });
      alert('调货成功');
    } catch (err) {
      alert(`调货失败：${err.message}`);
    }
  };
  
  const close = () => {
    isVisible.value = false;
    emit('close');
  };
  
  const relatedclose = () => {
    isVisible.value = false;
  };
  
  defineExpose({ show, relatedclose });
  </script>
  
  <style scoped>
  @import './popup-style.css';
  </style>
  