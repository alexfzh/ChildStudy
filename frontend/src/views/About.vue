<script setup>
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { systemAPI } from "@/api"

const versionInfo = ref(null)
const upgradeLog = ref([])
const upgrading = ref(false)

const loadVersion = async () => {
  try {
    versionInfo.value = await systemAPI.getVersion()
  } catch (e) {
    ElMessage.error("版本信息加载失败")
  }
}

const loadUpgradeLog = async () => {
  try {
    upgradeLog.value = await systemAPI.getUpgradeLog()
  } catch (e) {
    /* noop */
  }
}

const doUpgrade = async () => {
  upgrading.value = true
  try {
    const res = await systemAPI.triggerUpgrade()
    ElMessage.success(res.message || "升级完成")
    await loadVersion()
    await loadUpgradeLog()
  } catch (e) {
    ElMessage.error("升级失败")
  } finally {
    upgrading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadVersion(), loadUpgradeLog()])
})
</script>

<template>
  <div class="space-y-5">
    <!-- 版本信息卡片 -->
    <div class="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-200">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-xl font-bold text-slate-800">🌱 学业成长系统</h2>
          <div class="text-sm text-slate-600 mt-1">
            版本 <span class="font-mono font-bold text-brand-600 text-base">{{ versionInfo?.version || "..." }}</span>
            <span class="text-slate-400">· 构建于 {{ versionInfo?.build_time || "..." }}</span>
          </div>
          <div class="flex flex-wrap gap-3 mt-3 text-xs text-slate-500">
            <span class="px-2 py-1 bg-white rounded border border-slate-200"
              >🐍 Python {{ versionInfo?.python_version || "..." }}</span
            >
            <span class="px-2 py-1 bg-white rounded border border-slate-200">🗄️ SQLite</span>
            <span
              v-if="versionInfo?.debug_mode"
              class="px-2 py-1 bg-amber-100 text-amber-700 rounded border border-amber-200"
              >⚠️ 调试模式</span
            >
          </div>
        </div>
        <div class="flex flex-col gap-2">
          <el-button size="small" :loading="!versionInfo" @click="loadVersion">刷新版本</el-button>
          <el-button size="small" type="primary" :loading="upgrading" @click="doUpgrade">检查升级</el-button>
        </div>
      </div>
    </div>

    <!-- 升级日志 -->
    <div v-if="upgradeLog.length" class="card p-5">
      <h3 class="text-base font-semibold text-slate-800 mb-3">📋 升级历史</h3>
      <div class="space-y-2">
        <div v-for="log in upgradeLog" :key="log.timestamp" class="flex items-start gap-3 p-3 rounded-lg bg-slate-50">
          <span
            class="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
            :class="log.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
          >
            {{ log.status === "success" ? "✅ 成功" : "❌ 失败" }}
          </span>
          <div class="flex-1 min-w-0">
            <div class="text-sm text-slate-700 font-medium">{{ log.from_version }} → {{ log.to_version }}</div>
            <div class="text-xs text-slate-500 mt-0.5">{{ log.detail }}</div>
            <div class="text-xs text-slate-400 mt-1">{{ log.timestamp }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 技术栈 -->
    <div class="card p-5 bg-slate-50 border-slate-200">
      <h3 class="font-semibold text-slate-800 mb-2">技术栈</h3>
      <div class="text-sm text-slate-600 leading-relaxed space-y-1">
        <div>⚙️ 后端: FastAPI + SQLAlchemy + SQLite</div>
        <div>🎨 前端: Vue 3 + Element Plus + ECharts</div>
        <div>📦 数据存储: 本地 SQLite，不上传云端</div>
        <div>🔒 隐私优先 · 离线可用 · 无外部依赖</div>
      </div>
    </div>
  </div>
</template>
