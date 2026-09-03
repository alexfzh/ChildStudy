import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

export default defineConfig({
  plugins: [
    vue(),
    // element-plus 按需引入：模板组件 + API 自动按需导入（含样式）
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    // LAN 访问：绑 0.0.0.0 让同网段设备能 hit 到 vite dev server
    // 生产部署用 python main.py 同源托管，前端不走 vite，不需要这个
    host: "0.0.0.0",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ["vue", "vue-router", "pinia"],
          // element-plus 已改为按需引入（unplugin），不可再列 "element-plus"
          // 否则全量包会被 manualChunks 原样打回（938KB）
          charts: ["echarts", "vue-echarts"],
        },
      },
    },
  },
});

// touch: force hmr restart
