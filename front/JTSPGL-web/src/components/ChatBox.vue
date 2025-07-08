<template>
    <div class="chat-box">
        <div class="chat-history" id="chat-history"></div>
            <div class="chat-input-area">
                <div class="input-group">
                <input
                    type="text"
                    class="form-control"
                    id="chat-input"
                    placeholder="请输入您的问题..."
                />
                <button class="btn btn-dark" onclick="sendMessage()">
                    发送
                </button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
      sendMessage() {
        const input = document.getElementById("chat-input");
        const history = document.getElementById("chat-history");
        if (input.value.trim()) {
          const row = document.createElement("div");
          row.className = "chat-message-row sender";

          const msg = document.createElement("div");
          msg.className = "chat-message";
          msg.textContent = input.value;

          row.appendChild(msg);
          history.appendChild(row);

          // 添加模拟回复
          setTimeout(() => {
            const botRow = document.createElement("div");
            botRow.className = "chat-message-row receiver";

            const botMsg = document.createElement("div");
            botMsg.className = "chat-message";
            botMsg.textContent = "已收到您的消息：" + input.value;

            botRow.appendChild(botMsg);
            history.appendChild(botRow);

            history.scrollTop = history.scrollHeight;
          }, 500);

          history.scrollTop = history.scrollHeight;
          input.value = "";
        }
      }
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
    }
    .chat-message-row {
        display: flex;
        flex-direction: row;
    }
    .chat-message {
        background-color: #e0f0ff;
        padding: 8px 12px;
        border-radius: 10px;
        max-width: 80%;
        word-break: break-word;
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
</style>