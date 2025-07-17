<template>
  <div class="chat-box">
    <div class="chat-history" ref="chatHistory">
      <div
        v-for="(message, index) in messages"
        :key="index"
        class="chat-message-row"
        :class="message.sender"
      >
        <div class="chat-message">
          <!-- 文本消息 -->
          <template v-if="message.type === 'text'">
            {{ message.text }}
          </template>
          <!-- 图片消息 -->
          <template v-else-if="message.type === 'image'">
            <img :src="message.url" class="chat-image" alt="图片" @load="scrollToBottom" />
          </template>
        </div>
      </div>
    </div>
    <div class="chat-input-area d-flex align-items-center">
  <div class="chat-input flex-grow-1 me-2">
    <input
      type="text"
      class="form-control"
      v-model="inputMessage"
      placeholder="请输入您的问题..."
      @keyup.enter="sendMessage"
    />
  </div>
  <div class="chat-send-btn">
    <button class="btn btn-primary" @click="sendMessage">发送</button>
  </div>
</div>
  </div>
</template>

<script setup>
import { ref, nextTick } from "vue";
import axios from "axios";
import { showToast } from '@/utils/toast'
const inputMessage = ref("");
const messages = ref([]);
const chatHistory = ref(null);

const sendMessage = async () => {
  if (inputMessage.value.trim()) {
    messages.value.push({
      type: "text",
      text: inputMessage.value,
      sender: "sender",
    });

    const sentText = inputMessage.value;
    inputMessage.value = "";

    scrollToBottom();

    try {
      const response = await axios.post("http://localhost:5000/chatting", {
        text: sentText,
      });
      if (response.data.isString){
        messages.value.push({
          type: "text",
          text: response.data.result,
          sender: "receiver",
        });
      }
      else{
        messages.value.push({
          type: "image",
          url: response.data.result,
          sender: "receiver"
        });
      }
    } catch (error) {
      messages.value.push({
        type: "text",
        text: `处理出错: ${error.response?.data?.error || error.message}`,
        sender: "receiver",
      });
    }
  }
};

const handleImageUpload = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  // 创建本地URL用于预览
  const imageUrl = URL.createObjectURL(file);
  alert(imageUrl);
  // 添加到消息列表
  messages.value.push({
    type: "image",
    url: imageUrl,
    sender: "receiver",
    file: file // 保留文件对象用于后续上传
  });

  // 重置文件输入，允许重复选择同一文件
  event.target.value = null;
  
  scrollToBottom();
};

const scrollToBottom = () => {
  nextTick(() => {
    chatHistory.value.scrollTop = chatHistory.value.scrollHeight;
  });
};
</script>

<style scoped>
.chat-box {
  background: linear-gradient(to bottom right, #f5f7fa, #f5f7fa);
  padding: 12px;
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
  background: linear-gradient(to bottom right, #eef0f3, #fafcff);
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
  white-space: pre-wrap;
}

.receiver .chat-message {
  background-color: #e0f0ff;
  border-top-left-radius: 0;
}

.receiver .chat-message,
.sender .chat-message {
  background-color: rgba(255, 255, 255, 0.8); /* 半透明白底，提升可读性 */
}


.sender .chat-message {
  background-color: #d1e7dd;
  border-top-right-radius: 0;
}

/* 图片消息样式 */
.chat-image {
  max-width: 100%;
  max-height: 150px;
  border-radius: 8px;
  display: block;
}

.chat-input-area {
  display: flex;
  gap: 8px;
}

.input-group {
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid #ced4da;
  display: flex;
  align-items: center;
}

.input-group .form-control {
  border: none;
  border-radius: 10px;
  padding: 10px 15px;
  flex: 1;
}

.input-group .form-control:focus {
  box-shadow: none;
  outline: none;
}

.input-group .btn {
  border-radius: 8px;
  padding: 10px 15px;
  border: none;
  transition: background-color 0.3s;
}

.input-group .btn-dark {
  background-color: #4a86e8;
  color: white;
}

.input-group .btn-dark:hover {
  background-color: #3a76d8;
}

.input-group .btn-secondary {
  background-color: #6c757d;
  color: white;
}

.input-group .btn-secondary:hover {
  background-color: #5a6268;
}
</style>