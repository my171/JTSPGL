<template>
  <div class="container">
    <h1>文本处理工具</h1>
    <div class="input-area">
      <input 
        type="text" 
        v-model="inputText" 
        placeholder="输入文本..."
        @keyup.enter="processText"
      />
      <button @click="processText">处理文本</button>
    </div>
    <div class="output-area">
      <textarea 
        readonly 
        v-model="outputText" 
        placeholder="处理结果将显示在这里..."
      ></textarea>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import axios from 'axios';

const inputText = ref('');
const outputText = ref('');

const processText = async () => {
  if (!inputText.value.trim()) {
    outputText.value = "请输入有效文本";
    return;
  }

  try {
    const response = await axios.post('http://localhost:5000/process', {
      text: inputText.value
    });
    outputText.value = response.data.result;
  } catch (error) {
    outputText.value = `处理出错: ${error.response?.data?.error || error.message}`;
  }
};
</script>

<style scoped>
.container {
  max-width: 600px;
  margin: 2rem auto;
  padding: 20px;
  font-family: Arial, sans-serif;
}

h1 {
  text-align: center;
  color: #2c3e50;
}

.input-area {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
}

button {
  padding: 10px 20px;
  background-color: #42b983;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #359c6d;
}

textarea {
  width: 100%;
  height: 200px;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  resize: vertical;
}
</style>
