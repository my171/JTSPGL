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
    showPopup(html) {
    document.getElementById("popup-content").innerHTML = html;
    document.getElementById("popup-panel").classList.add("show");
    },

    closePopup() {
    document.getElementById("popup-panel").classList.remove("show");
    document.getElementById("right-panel").style.transform =
        "translateX(0)";
    },
    showApprovalDetail(productId) {
        document.getElementById("right-panel").style.transform =
          "translateX(-400px)";
        const infoMap = {
          P10001: {
            status: "待审核",
            decisionTime: "-",
            reviewTime: "-",
            dispatchTime: "-",
            receivedTime: "-",
            from: "华东智能仓",
            to: "南京新街口店",
          },
          P10006: {
            status: "已完成",
            decisionTime: "2025-07-01 10:00",
            reviewTime: "2025-07-02 11:00",
            dispatchTime: "2025-07-03 15:30",
            receivedTime: "2025-07-05 09:15",
            from: "华北中心仓",
            to: "北京王府井旗舰店",
          },
          P10002: {
            status: "审核不通过",
            decisionTime: "2025-06-28 14:00",
            reviewTime: "2025-06-29 09:30",
            dispatchTime: "-",
            receivedTime: "-",
            from: "华南枢纽仓",
            to: "广州天河城店",
          },
          P10003: {
            status: "待出库",
            decisionTime: "2025-06-30 08:00",
            reviewTime: "-",
            dispatchTime: "-",
            receivedTime: "-",
            from: "西南分拨中心",
            to: "成都春熙路店",
          },
          P10004: {
            status: "发货中",
            decisionTime: "2025-07-01 12:00",
            reviewTime: "2025-07-01 13:30",
            dispatchTime: "2025-07-02 10:00",
            receivedTime: "-",
            from: "东北冷链仓",
            to: "西安钟楼店",
          },
          P10005: {
            status: "待收货",
            decisionTime: "2025-07-02 16:00",
            reviewTime: "2025-07-03 09:00",
            dispatchTime: "2025-07-04 14:30",
            receivedTime: "-",
            from: "华东智能仓",
            to: "上海徐家汇店",
          },
        };

        const item = infoMap[productId] || {
          status: "未知",
          decisionTime: "-",
          reviewTime: "-",
          dispatchTime: "-",
          receivedTime: "-",
          from: "-",
          to: "-",
        };
        const html = `
      <h5>审批详情：${productId}</h5>
      <p><strong>当前状态：</strong>${item.status}</p>
      <p><strong>调出仓库：</strong>${item.from}</p>
      <p><strong>调入商店：</strong>${item.to}</p>
      <p><strong>决策时间：</strong>${item.decisionTime}</p>
      <p><strong>审核时间：</strong>${item.reviewTime}</p>
      <p><strong>发货时间：</strong>${item.dispatchTime}</p>
      <p><strong>收货时间：</strong>${item.receivedTime}</p>
    `;
        showPopup(html);
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