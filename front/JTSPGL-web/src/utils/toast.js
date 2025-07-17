// src/utils/toast.js
import { Toast } from "bootstrap";

/**
 * 显示一个带样式的 Toast 提示
 * @param {string} message - 提示文字
 * @param {'primary'|'success'|'warning'|'danger'} type - 提示类型
 */
export function showToast(message, type = "primary") {
  const toastEl = document.getElementById("successToast");
  const toastMessageEl = document.getElementById("toastMessage");

  // 支持 success / warning / danger 类型
  const bgClassMap = {
    primary: "text-bg-primary",
    success: "text-bg-success",
    warning: "text-bg-warning",
    danger: "text-bg-danger",
  };

  // 移除旧的类型类
  toastEl.classList.remove(...Object.values(bgClassMap));

  // 添加新的类型类
  toastEl.classList.add(bgClassMap[type]);

  // 设置提示文字
  toastMessageEl.textContent = message;

  // 显示 Toast
  new Toast(toastEl, { delay: 3000 }).show();
}
