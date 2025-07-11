<!--ChatBox.vue-->
<template>
  <div class="chat-box">
    <div class="chat-history" ref="chatHistory">
      <div 
        v-for="(message, index) in messages" 
        :key="index"
        class="chat-message-row"
        :class="message.sender"
      >
        <div class="chat-message">{{ message.text }}</div>
      </div>
    </div>
    <div class="chat-input-area">
      <div class="input-group">
        <input
          type="text"
          class="form-control"
          v-model="inputMessage"
          placeholder="请输入您的问题..."
          @keyup.enter="sendMessage"
        />
        <button class="btn btn-dark" @click="sendMessage">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue';
import axios from 'axios';

const inputMessage = ref('');
const messages = ref([]);
const chatHistory = ref(null);

const sendMessage = async () => {
  if (inputMessage.value.trim()) {
    messages.value.push({
      text: inputMessage.value,
      sender: 'sender'
    });
    
    const sentText = inputMessage.value;
    inputMessage.value = '';

    scrollToBottom();
    
    try {
        const response = await axios.post('http://localhost:5000/chatting', {
            text: sentText
        });
        messages.value.push({
            text: response.data.result,
            sender: 'receiver'
        });
    } catch (error) {
        messages.value = `处理出错: ${error.response?.data?.error || error.message}`;
    }
    //inputMessage.value = '';之前清空过，此处多余
  }
};

const scrollToBottom = () => {
  nextTick(() => {
    chatHistory.value.scrollTop = chatHistory.value.scrollHeight;
  });
};
</script>

<style scoped>
.chat-box {
  background-color: #fff;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 8px;
  height: 230px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  z-index: 0;
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 8px;
  padding-right: 5px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  background-color: #f9f9f9;
  border-radius: 8px;
}

.chat-message-row {
  display: flex;
  flex-direction: row;
}

.chat-message-row.receiver {
  justify-content: flex-start;
}

.chat-message-row.sender {
  justify-content: flex-end;
}

.chat-message {
  padding: 8px 12px;
  border-radius: 10px;
  max-width: 80%;
  word-break: break-word;
}

.receiver .chat-message {
  background-color: #e0f0ff;
  border-top-left-radius: 0;
}

.sender .chat-message {
  background-color: #d1e7dd;
  border-top-right-radius: 0;
}

.chat-input-area {
  display: flex;
  gap: 8px;
}

.input-group {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #ced4da;
}

.input-group .form-control {
  border: none;
  border-radius: 10px;
  padding: 10px 15px;
}

.input-group .form-control:focus {
  box-shadow: none;
  outline: none;
}

.input-group .btn {
  border-radius: 8px;
  padding: 10px 20px;
  background-color: #4a86e8;
  color: white;
  border: none;
  transition: background-color 0.3s;
}

.input-group .btn:hover {
  background-color: #3a76d8;
}
</style>