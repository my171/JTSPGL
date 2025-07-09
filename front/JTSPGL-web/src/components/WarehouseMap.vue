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
  { id: 'WH001', name: '华北中心仓', top: '280px', left: '700px' },
  { id: 'WH002', name: '华东智能仓', top: '380px', left: '780px' },
  { id: 'WH003', name: '华南枢纽仓', top: '505px', left: '680px' },
  { id: 'WH004', name: '西南分拨中心', top: '410px', left: '550px' },
  { id: 'WH005', name: '东北冷链仓', top: '160px', left: '870px' }
];

const showWarehouse = (id, name) => {
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
  background-size: 820px  600px;
  background-repeat: no-repeat;
  background-position: center;
}

.warehouse {
  position: absolute;
  cursor: pointer;
  transition: transform 0.2s, background-color 0.2s;
  padding: 6px 12px;
  border-radius: 8px;
  background-color: #4ad051;
  color: white;
  font-size: 14px;
}

.warehouse:hover {
  background-color: #54ea5b;
  transform: scale(1.05);
}
</style>