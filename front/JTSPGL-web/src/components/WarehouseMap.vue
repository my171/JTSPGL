<!--WarehouseMap.vue-->
<template>
  <div class="map-container">
    <div class="map-area" ref="mapContainer">
      <div
        v-for="warehouse in warehouses"
        :key="warehouse.id"
        class="warehouse"
        :style="warehouse.style"
        @click="showWarehouse(warehouse.id, warehouse.name)"
      >
        {{ warehouse.name }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";

const emit = defineEmits(["show-warehouse"]);
const mapContainer = ref(null);

// 仓库数据
const warehouses = ref([
  { id: "WH001", name: "华北中心仓", style: {} },
  { id: "WH002", name: "华东智能仓", style: {} },
  { id: "WH003", name: "华南枢纽仓", style: {} },
  { id: "WH004", name: "西南分拨中心", style: {} },
  { id: "WH005", name: "东北冷链仓", style: {} },
]);

const warehousePositions = ref([
  { id: "WH001", name: "华北中心仓", x: 0.2, y: 0 },
  { id: "WH002", name: "华东智能仓", x: 0.35, y: 0.15 },
  { id: "WH003", name: "华南枢纽仓", x: 0.175, y: 0.35 },
  { id: "WH004", name: "西南分拨中心", x: 0, y: 0.2 },
  { id: "WH005", name: "东北冷链仓", x: 0.5, y: -0.3 },
]);


const detailInfo = ref(localStorage.getItem('DetailInfo'));




// 计算按钮位置
const calculatePositions = () => {
  if (!mapContainer.value) return;

  const containerRect = mapContainer.value.getBoundingClientRect();
  const containerWidth = containerRect.width;
  const containerHeight = containerRect.height;

  // 为每个仓库计算位置
  warehouses.value = warehousePositions.value.map((warehouse) => {
    // 计算特殊定位公式：left = 容器高度*25% + 容器宽度*50%
    const left = containerWidth * 0.5 + containerHeight * warehouse.x;

    // 你可以为每个仓库设置不同的top值，这里示例使用固定值
    const top = containerHeight * (0.5 + warehouse.y); // 示例值，可以调整

    return {
      ...warehouse,
      style: {
        left: `${left}px`,
        top: `${top}px`,
        transform: "translate(-50%, -50%)", // 使按钮中心对准定位点
      },
    };
  });
};

const baseFontSize = 7.5; // 基础字体大小(px)
const basePadding = 2; // 基础内边距(px)

const calculateSizes = () => {
  if (!mapContainer.value) return;

  const containerHeight = mapContainer.value.clientHeight;
  const scale = containerHeight / 200; // 1200是设计时的基准宽度

  warehouses.value = warehouses.value.map((wh) => ({
    ...wh,
    style: {
      ...wh.style,
      fontSize: `${baseFontSize * scale}px`,
      padding: `${basePadding * scale}px ${basePadding * 2 * scale}px`,
    },
  }));
};

// 使用ResizeObserver监听尺寸变化
let resizeObserver;
let resizeObserver2;
onMounted(() => {
  calculatePositions();
  calculateSizes();
  resizeObserver = new ResizeObserver(calculatePositions);
  resizeObserver2 = new ResizeObserver(calculateSizes);
  if (mapContainer.value) {
    resizeObserver.observe(mapContainer.value);
    resizeObserver2.observe(mapContainer.value);
  }
  window.addEventListener("resize", calculateSizes);
  window.addEventListener("resize", calculatePositions);
  window.addEventListener('storage', handleStorageChange);
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
  if (resizeObserver2) {
    resizeObserver2.disconnect();
  }
  window.removeEventListener("resize", calculateSizes);
  window.removeEventListener("resize", calculatePositions);
  window.removeEventListener('storage', handleStorageChange);
});

// 处理storage变化
const handleStorageChange = (e) => {
  if (e.key === 'DetailInfo') {
    detailInfo.value = e.newValue;
  }
};

const showWarehouse = (id, name) => {
  emit("show-warehouse", id, name);
};
</script>

<style scoped>
.map-container {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-area {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: #e6ecf2;
  border: 1px solid #ccc;
  border-radius: 10px;
  background-image: url("@images/MapImg.png");
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
}

.warehouse {
  position: absolute;
  cursor: pointer;
  transition: transform 0.2s, background-color 0.2s;
  padding: 6px 12px;
  border-radius: 12px;
  background-color: #4ad051;
  color: white;
  font-size: 14px;
  white-space: nowrap;
  transform: translate(-50%, -50%) scale(1);
  transform-origin: center;
}

.warehouse:hover {
  background-color: #54ea5b;
  transform: scale(1.05);
}
</style>
