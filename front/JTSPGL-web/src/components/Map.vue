<template>
  <div class="image-box-container">
    <!-- 矩形框（带背景图片） -->
    <div class="image-box" :style="{ backgroundImage: `url(${backgroundImage})` }">
      <!-- 按钮组 -->
      <div class="buttons-container">
        <button 
          v-for="(btn, index) in buttons" 
          :key="index"
          @click="handleButtonClick(btn.action)"
          class="custom-button"
        >
          {{ btn.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const backgroundImage = ref('/src/images/MapImg.png');

// 按钮配置
const buttons = ref([
  { label: '按钮1', action: 'action1' },
  { label: '按钮2', action: 'action2' },
  { label: '按钮3', action: 'action3' },
]);

// 按钮点击事件
const handleButtonClick = (action) => {
  console.log(`点击了按钮，执行操作: ${action}`);
  // 可以在这里添加按钮逻辑，比如 emit 事件或调用方法
  if (action === 'action1') {
    window.location.hash = "asdf";
    //TODO:编写按钮按下后的逻辑1
  } else if (action === 'action2') {
    //TODO:编写按钮按下后的逻辑2
  } else if (action === 'action3') {
    //TODO:编写按钮按下后的逻辑3
  }
};
</script>

<style scoped>
.image-box-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

.image-box {
  width: 600px;
  height: 400px;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  border: 2px solid #333;
  border-radius: 8px;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.buttons-container {
  display: flex;
  gap: 10px;
  position: absolute;
  bottom: 20px;
}

.custom-button {
  padding: 10px 20px;
  background-color: rgba(255, 255, 255, 0.8);
  border: 1px solid #333;
  border-radius: 4px;
  cursor: pointer;
  font-weight: bold;
  transition: background-color 0.3s;
}

.custom-button:hover {
  background-color: rgba(255, 255, 255, 1);
}
</style>

<!--以下是原html文件部分参考-->


<!--
<template>
    <div class="map-area">
        <div
            class="warehouse"
            style="top: 80px; left: 100px"
            onclick="showWarehouseInfo('WH001', '华北中心仓')"
        >
        华北中心仓
        </div>
        <div
            class="warehouse"
            style="top: 120px; left: 280px"
            onclick="showWarehouseInfo('WH002', '华东智能仓')"
        >
        华东智能仓
        </div>
        <div
            class="warehouse"
            style="top: 220px; left: 160px"
            onclick="showWarehouseInfo('WH003', '华南枢纽仓')"
        >
        华南枢纽仓
        </div>
        <div
            class="warehouse"
            style="top: 300px; left: 80px"
            onclick="showWarehouseInfo('WH004', '西南分拨中心')"
        >
        西南分拨中心
        </div>
        <div
            class="warehouse"
            style="top: 350px; left: 260px"
            onclick="showWarehouseInfo('WH005', '东北冷链仓')"
        >
        东北冷链仓
        </div>
    </div>
</template>

<script>
export default {
    data() {
        return {
            currentTime: ""
        };
    },
    mounted() {
        this.updateTime();
        this.timer = setInterval(this.updateTime, 1000);
    },
    beforeDestroy() {
        clearInterval(this.timer);
    },
    methods: {
        updateTime() {
            const now = new Date();
            this.currentTime = now.toLocaleString();
        }
    }
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
</style>
-->