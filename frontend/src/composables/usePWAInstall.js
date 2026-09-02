import { ref, onMounted } from "vue";

/**
 * PWA 安装提示（兼容 Android Chrome + iOS Safari + 华为鸿蒙）
 *
 * Android Chrome: 监听 beforeinstallprompt，可主动触发系统安装弹窗
 * iOS Safari:  没有 beforeinstallprompt，改为显示手动添加指引
 * 鸿蒙浏览器:  基于 Chromium 内核，通常也支持 beforeinstallprompt
 */
export function usePWAInstall() {
  const deferredPrompt = ref(null);
  const isInstallable = ref(false);
  const isStandalone = ref(false);
  const dismissed = ref(false);
  const platform = ref("unknown");

  function detectPlatform() {
    const ua = navigator.userAgent || "";
    if (/HarmonyOS/i.test(ua) || /HUAWEI/i.test(ua)) {
      platform.value = "harmony";
    } else if (/Android/i.test(ua)) {
      platform.value = "android";
    } else if (/iPhone|iPad|iPod/i.test(ua)) {
      platform.value = "ios";
    } else if (/Macintosh/i.test(ua) && navigator.maxTouchPoints > 1) {
      platform.value = "ipad";
    } else {
      platform.value = "desktop";
    }

    // 检测是否已作为 PWA 运行
    isStandalone.value =
      window.matchMedia("(display-mode: standalone)").matches ||
      !!window.navigator.standalone;
  }

  async function install() {
    if (!deferredPrompt.value) return false;
    deferredPrompt.value.prompt();
    const { outcome } = await deferredPrompt.value.userChoice;
    console.log(`[PWA] 安装结果: ${outcome}`);
    deferredPrompt.value = null;
    isInstallable.value = false;
    return outcome === "accepted";
  }

  function dismiss() {
    dismissed.value = true;
    try {
      localStorage.setItem("pwa_install_dismissed", "1");
    } catch { /* noop */ }
  }

  onMounted(() => {
    detectPlatform();

    // 恢复已 dismissed 状态
    try {
      if (localStorage.getItem("pwa_install_dismissed") === "1") {
        dismissed.value = true;
      }
    } catch { /* noop */ }

    // Android Chrome / 鸿蒙: beforeinstallprompt
    window.addEventListener("beforeinstallprompt", (e) => {
      e.preventDefault();
      deferredPrompt.value = e;
      isInstallable.value = true;
      console.log("[PWA] 检测到可安装");
    });

    // 监听 installed 事件
    window.addEventListener("appinstalled", () => {
      console.log("[PWA] 已安装");
      deferredPrompt.value = null;
      isInstallable.value = false;
      dismissed.value = false;
    });

    // 监听 display-mode 变化
    window.matchMedia("(display-mode: standalone)").addEventListener("change", (e) => {
      isStandalone.value = e.matches;
    });
  });

  return {
    isInstallable,
    isStandalone,
    dismissed,
    platform,
    install,
    dismiss,
  };
}
