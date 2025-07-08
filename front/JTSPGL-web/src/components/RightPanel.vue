<template>    <div class="container-fluid">
      <div class="row">
        <div class="col-md-3 right-panel" id="right-panel">
          <h5>AI 实时预警</h5>
          <textarea class="form-control mb-3" rows="3" readonly>
暂无预警</textarea
          >

          <h5 class="mt-4">审批流进度</h5>
          <div id="approval-status">
            <button
              class="approval-button status-green"
              onclick="showApprovalDetail('P10006')"
            >
              商品 P10006 - 已完成
            </button>
            <button
              class="approval-button status-orange"
              onclick="showApprovalDetail('P10005')"
            >
              商品 P10005 - 待收货
            </button>
            <button
              class="approval-button status-yellow"
              onclick="showApprovalDetail('P10004')"
            >
              商品 P10004 - 发货中
            </button>
            <button
              class="approval-button status-blue"
              onclick="showApprovalDetail('P10003')"
            >
              商品 P10003 - 待出库
            </button>
            <button
              class="approval-button status-red"
              onclick="showApprovalDetail('P10002')"
            >
              商品 P10002 - 审核不通过
            </button>
            <button
              class="approval-button status-gray"
              onclick="showApprovalDetail('P10001')"
            >
              商品 P10001 - 待审核
            </button>
          </div>
        </div>
      </div>
    </div>
    <div class="popup-panel" id="popup-panel">
      <button
        class="btn btn-sm btn-outline-secondary mb-3"
        onclick="closePopup()"
      >
        关闭
      </button>
      <div id="popup-content">加载中...</div>
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
.header-time {
    font-size: 28px;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin-bottom: 10px;
}
</style>