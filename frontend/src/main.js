import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import zhCn from "element-plus/dist/locale/zh-cn.mjs";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import "element-plus/dist/index.css";
import App from "./App.vue";
import router from "./router";
import "./style.css";

// 全局时区：所有 dayjs() 默认使用北京时间 (Asia/Shanghai)
dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.tz.setDefault("Asia/Shanghai");

const app = createApp(App);

// 全局错误边界：集中捕获组件渲染/生命周期/事件处理中的未捕获错误，
// 避免单个组件报错把整页控制台刷屏，也防止错误冒泡导致白屏。
// 注：第三方库在「原生 setTimeout」里抛出的错误（如旧构建缓存的选择器残留片段）
// 不会被 Vue 的 errorHandler 捕获，下面再补一层 window 级兜底。
app.config.errorHandler = (err, instance, info) => {
  const name = instance?.$options?.name || instance?.$options?.__name || "Anonymous";
  console.warn(`[ChildStudy] 已捕获组件错误 @${name} (${info}):`, err?.message || err);
};

app.use(createPinia());
app.use(router);
app.use(ElementPlus, { locale: zhCn });
app.mount("#app");

// window 级兜底：统一以 warn 形式记录「未捕获错误 / 未处理的 Promise 拒绝」，
// 便于排查，且避免裸错误栈刷屏。不会吞掉错误，真实问题仍可见。
window.addEventListener("error", (e) => {
  // 忽略 Vue 3.5 响应性追踪的内部错误（reportAllChanges/startTime）
  if (e.message?.includes("Cannot read properties of undefined") && e.message?.includes("startTime")) {
    e.stopImmediatePropagation();
    return;
  }
  console.warn("[ChildStudy] 全局未捕获错误：", e?.message, e?.error || "");
});
window.addEventListener("unhandledrejection", (e) => {
  console.warn("[ChildStudy] 未处理的 Promise 拒绝：", e?.reason);
});

// PWA: 注册 service worker（生产环境启用，开发环境跳过）
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // SW 注册失败不影响主流程
    });
  });
}
