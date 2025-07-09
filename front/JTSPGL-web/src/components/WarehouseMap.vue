<template>
  <div class="map-area">
    <div
      v-for="warehouse in warehouses"
      :key="warehouse.id"
      class="warehouse"
      :style="{ top: warehouse.top, left: warehouse.left }"
      @click="showWarehouse(warehouse.id, warehouse.name)"
    >
      {{ warehouse.name }}
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['show-warehouse']);

const warehouses = [
  { id: 'WH001', name: '华北中心仓', top: '80px', left: '100px' },
  { id: 'WH002', name: '华东智能仓', top: '120px', left: '280px' },
  { id: 'WH003', name: '华南枢纽仓', top: '220px', left: '160px' },
  { id: 'WH004', name: '西南分拨中心', top: '300px', left: '80px' },
  { id: 'WH005', name: '东北冷链仓', top: '350px', left: '260px' }
];

const showWarehouse = (id, name) => {
  window.location.hash = "asdasf"
  emit('show-warehouse', id, name);
};
</script>

<style scoped>
.map-area {
  flex: 1;
  background-color: #e6ecf2;
  border: 1px solid #ccc;
  border-radius: 10px;
  position: relative;
  margin-bottom: 15px;
  background-image: url('@images/MapImg.png');
  background-size: cover;
  background-repeat: no-repeat;
  background-position: center;
}

.warehouse {
  position: absolute;
  cursor: pointer;
  transition: transform 0.2s, background-color 0.2s;
  padding: 6px 12px;
  border-radius: 8px;
  background-color: #5baaff;
  color: white;
  font-size: 14px;
}

.warehouse:hover {
  background-color: #0077f7;
  transform: scale(1.05);
}
</style>