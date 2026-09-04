<script setup>
import { ref, computed, watch, onMounted } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import dayjs from "dayjs"
import { useChildStore } from "@/stores/child"
import { reportsAPI } from "@/api"

const childStore = useChildStore()
const reports = ref([])
const loading = ref(false)

// 当前查看的报告
const activeReport = ref(null)

// "导出上下文"对话框
const exportDialogVisible = ref(false)
const exportPeriod = ref(90)
const exportContextMd = ref("")
const exportLoading = ref(false)
const exportChildName = ref("")

// "导入报告"对话框
const importDialogVisible = ref(false)
const importForm = ref({
  title: "",
  source: "",
  summary: "",
  raw_markdown: "",
})

// ============== 列表 ==============
const loadReports = async () => {
  if (!childStore.currentId) return
  loading.value = true
  try {
    reports.value = await reportsAPI.list(childStore.currentId)
  } finally {
    loading.value = false
  }
}

watch(() => childStore.currentId, loadReports)
onMounted(loadReports)

// ============== 报告列表 inline 编辑 ==============
const editingId = ref(null)
const editTitle = ref("")
const editSummary = ref("")
const saving = ref(false)

const startEdit = (r) => {
  editingId.value = r.id
  editTitle.value = r.title
  editSummary.value = r.summary || ""
}

const cancelEdit = () => {
  editingId.value = null
  editTitle.value = ""
  editSummary.value = ""
}

const saveEdit = async (id) => {
  const title = editTitle.value.trim()
  const summary = editSummary.value.trim() || null
  if (!title) {
    ElMessage.warning("标题不能为空")
    return
  }
  saving.value = true
  try {
    const updated = await reportsAPI.update(id, { title, summary })
    const target = reports.value.find((x) => x.id === id)
    if (target) {
      Object.assign(target, updated)
    }
    if (activeReport.value?.id === id) {
      activeReport.value = updated
    }
    editingId.value = null
  } catch (e) {
    /* interceptor */
  } finally {
    saving.value = false
  }
}

// ============== 导出上下文 ==============
const openExportDialog = async () => {
  if (!childStore.currentId) {
    ElMessage.warning("请先选择孩子")
    return
  }
  exportDialogVisible.value = true
  exportContextMd.value = ""
  exportLoading.value = true
  try {
    const resp = await reportsAPI.exportContext(childStore.currentId, exportPeriod.value)
    exportContextMd.value = resp.context_markdown
    exportChildName.value = resp.child_name
  } finally {
    exportLoading.value = false
  }
}

const copyContext = async () => {
  try {
    await navigator.clipboard.writeText(exportContextMd.value)
    ElMessage.success("上下文已复制到剪贴板。打开 DeepSeek / Kimi / ChatGPT 粘贴即可")
  } catch (e) {
    // fallback: select textarea
    const ta = document.getElementById("export-md-textarea")
    if (ta) {
      ta.select()
      document.execCommand("copy")
      ElMessage.success("已复制")
    }
  }
}

// ============== 导入报告 ==============
const openImportDialog = () => {
  if (!childStore.currentId) {
    ElMessage.warning("请先选择孩子")
    return
  }
  importForm.value = { title: "", source: "", summary: "", raw_markdown: "" }
  importDialogVisible.value = true
}

const submitImport = async () => {
  const f = importForm.value
  if (!f.title.trim()) {
    ElMessage.warning("请填写报告标题")
    return
  }
  if (!f.raw_markdown.trim()) {
    ElMessage.warning("请粘贴 AI 输出内容")
    return
  }
  try {
    await reportsAPI.create({
      child_id: childStore.currentId,
      title: f.title.trim(),
      source: f.source.trim() || null,
      summary: f.summary.trim() || null,
      raw_markdown: f.raw_markdown.trim(),
    })
    ElMessage.success("报告已保存")
    importDialogVisible.value = false
    await loadReports()
  } catch (e) {
    /* axios interceptor */
  }
}

// ============== 详情 ==============
const openReport = async (id) => {
  activeReport.value = await reportsAPI.get(id)
}

const closeReport = () => {
  activeReport.value = null
}

// ============== 删除 ==============
const deleteReport = async (id, title) => {
  try {
    await ElMessageBox.confirm(`确认删除报告「${title}」？此操作不可恢复。`, "删除报告", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
    await reportsAPI.remove(id)
    ElMessage.success("已删除")
    if (activeReport.value?.id === id) closeReport()
    await loadReports()
  } catch (e) {
    /* user cancel or axios error */
  }
}

// ============== 简单 markdown 渲染（替换为换行 + 段落）==============
// 不用 marked 等依赖，够用即可
const renderMarkdown = (md) => {
  if (!md) return ""
  // 转义 HTML
  let html = md.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  // 标题
  html = html.replace(/^###### (.*$)/gim, "<h6>$1</h6>")
  html = html.replace(/^##### (.*$)/gim, "<h5>$1</h5>")
  html = html.replace(/^#### (.*$)/gim, "<h4>$1</h4>")
  html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>")
  html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>")
  html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>")
  // 加粗 + 斜体
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>")
  // 行内代码
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>")
  // 链接（带协议白名单，防 javascript:/data:/vbscript: XSS）
  // 仅允许 http(s) 与相对路径，命中其他协议则剥离链接但保留文本
  // 安全：url 插入 href 前必须转义引号/尖括号，否则 `http://a.com" onmouseover="..."`
  //       这类“安全协议”+空格+引号的 URL 可注入 HTML 属性（属性逃逸 XSS）。
  const SAFE_URL_RE = /^(https?:\/\/|\/|#)/i
  const escapeAttr = (s) => s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (m, text, url) => {
    const safe = SAFE_URL_RE.test(url.trim())
    return safe
      ? `<a href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`
      : `<span class="text-red-500" title="不安全的链接已被移除">${text}</span>`
  })
  // 表格 (简化：只识别 |---|)
  html = html.replace(/((?:\|[^\n]+\|\n)+)((?:\|[-:\s|]+\|\n))((?:\|[^\n]+\|\n?)+)/g, (m, header, sep, body) => {
    const ths = header
      .trim()
      .split("|")
      .slice(1, -1)
      .map((s) => `<th>${s.trim()}</th>`)
      .join("")
    const rows = body
      .trim()
      .split("\n")
      .map((line) => {
        const tds = line
          .split("|")
          .slice(1, -1)
          .map((s) => `<td>${s.trim()}</td>`)
          .join("")
        return `<tr>${tds}</tr>`
      })
      .join("")
    return `<table class="w-full text-sm border-collapse my-3"><thead><tr>${ths}</tr></thead><tbody>${rows}</tbody></table>`
  })
  // 列表（有序、无序）
  html = html.replace(/(^|\n)((?:- .+(?:\n|$))+)/g, (m, p, list) => {
    const items = list
      .trim()
      .split("\n")
      .map((l) => `<li>${l.replace(/^- /, "")}</li>`)
      .join("")
    return `${p}<ul class="list-disc list-inside space-y-1 my-2">${items}</ul>`
  })
  html = html.replace(/(^|\n)((?:\d+\. .+(?:\n|$))+)/g, (m, p, list) => {
    const items = list
      .trim()
      .split("\n")
      .map((l) => `<li>${l.replace(/^\d+\. /, "")}</li>`)
      .join("")
    return `${p}<ol class="list-decimal list-inside space-y-1 my-2">${items}</ol>`
  })
  // 水平线
  html = html.replace(/^---+$/gim, '<hr class="my-3 border-slate-200"/>')
  // 段落（双换行）
  html = html
    .split(/\n{2,}/)
    .map((para) => {
      para = para.trim()
      if (!para) return ""
      if (/^<(h\d|ul|ol|table|hr)/.test(para)) return para
      return `<p class="my-2 leading-relaxed">${para.replace(/\n/g, "<br/>")}</p>`
    })
    .join("\n")
  return html
}

const childName = computed(() => childStore.current?.name || "孩子")
</script>

<template>
  <div v-if="!childStore.currentId" class="card p-10 text-center text-slate-500">请先在「孩子档案」中添加孩子</div>

  <div v-else class="space-y-5">
    <!-- 顶部说明 + 三个动作按钮 -->
    <div class="card p-5">
      <div class="flex items-start justify-between flex-wrap gap-3 mb-4">
        <div>
          <h2 class="text-lg font-semibold text-slate-800">AI 报告管理 · {{ childName }}</h2>
          <p class="text-sm text-slate-500 mt-0.5">
            系统不直接调用 AI。你把孩子的学情数据导出，粘贴到外部 AI 跑分析，再把 AI 的输出粘回来保存。
          </p>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <button class="btn-primary" @click="openExportDialog">📤 导出当前数据为上下文</button>
        <button class="btn-secondary" @click="openImportDialog">📥 导入新报告</button>
      </div>
    </div>

    <!-- 工作流说明 -->
    <div class="card p-5 bg-slate-50 border-slate-200">
      <h3 class="font-semibold text-slate-800 mb-2">📋 三步工作流</h3>
      <ol class="text-sm text-slate-600 space-y-1.5 list-decimal list-inside leading-relaxed">
        <li><strong>导出</strong>：点上方"导出当前数据为上下文" → 系统生成孩子的学情 markdown → 一键复制到剪贴板</li>
        <li>
          <strong>外部跑 AI</strong>：打开
          <a class="text-brand-600 hover:underline" href="https://chat.deepseek.com" target="_blank">DeepSeek</a> /
          <a class="text-brand-600 hover:underline" href="https://kimi.moonshot.cn" target="_blank">Kimi</a> /
          <a class="text-brand-600 hover:underline" href="https://chatgpt.com" target="_blank">ChatGPT</a> / 其他 AI →
          粘贴 → 等它生成报告 → 复制 AI 输出
        </li>
        <li><strong>导入</strong>：回到系统，点"导入新报告" → 填标题 + 粘贴 AI 输出 → 保存。报告列表会显示</li>
      </ol>
    </div>

    <!-- 报告列表 -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold text-slate-800">📑 历史报告（{{ reports.length }}）</h3>
        <button class="btn-ghost text-xs" :disabled="loading" @click="loadReports">
          {{ loading ? "加载中…" : "刷新" }}
        </button>
      </div>

      <div v-if="reports.length === 0" class="text-center py-12 text-slate-400">
        <div class="text-4xl mb-2">📭</div>
        <div class="text-sm">还没有导入过报告</div>
      </div>

      <div v-else class="divide-y divide-slate-100">
        <div
          v-for="r in reports"
          :key="r.id"
          class="py-3 flex items-start justify-between gap-3 hover:bg-slate-50 -mx-3 px-3 rounded-lg"
          @click="editingId && editingId === r.id ? undefined : openReport(r.id)"
        >
          <div class="flex-1 min-w-0">
            <!-- inline edit mode -->
            <div v-if="editingId === r.id" class="space-y-2" @click.stop>
              <el-input
                v-model="editTitle"
                placeholder="标题"
                @keyup.enter="saveEdit(r.id)"
                @keyup.esc="cancelEdit"
                @blur="saveEdit(r.id)"
              />
              <el-input
                v-model="editSummary"
                type="textarea"
                :rows="2"
                placeholder="摘要（可选）"
                @keyup.esc="cancelEdit"
                @blur="saveEdit(r.id)"
              />
              <div class="text-[11px] text-slate-400">
                按 Enter / 失焦保存，Esc 取消{{ saving ? " · 保存中…" : "" }}
              </div>
            </div>
            <!-- view mode -->
            <div v-else class="flex items-center gap-2 mb-1">
              <span class="font-medium text-slate-800 truncate">{{ r.title }}</span>
              <span v-if="r.source" class="badge bg-slate-100 text-slate-600 text-[10px]">{{ r.source }}</span>
            </div>
            <div v-if="editingId !== r.id" class="text-xs text-slate-500">
              {{ dayjs(r.created_at).format("YYYY-MM-DD HH:mm") }}
              <span v-if="r.summary"> · {{ r.summary }}</span>
            </div>
          </div>
          <div v-if="editingId !== r.id" class="flex items-center gap-1 flex-shrink-0">
            <button class="text-slate-400 hover:text-brand-600 text-xs" title="编辑" @click.stop="startEdit(r)">
              ✏️
            </button>
            <button
              class="text-slate-400 hover:text-rose-600 text-xs"
              title="删除"
              @click.stop="deleteReport(r.id, r.title)"
            >
              🗑
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 导出对话框 -->
    <el-dialog v-model="exportDialogVisible" title="导出当前数据为上下文" width="720px" top="5vh">
      <div class="space-y-3">
        <div class="flex items-center gap-3">
          <span class="text-sm text-slate-600">数据周期：</span>
          <el-select v-model="exportPeriod" class="!w-32" @change="openExportDialog">
            <el-option label="最近 30 天" :value="30" />
            <el-option label="最近 90 天" :value="90" />
            <el-option label="最近 180 天" :value="180" />
            <el-option label="全部时间" :value="3650" />
          </el-select>
          <button class="btn-secondary text-xs" @click="openExportDialog">🔄 重新生成</button>
          <button class="btn-primary text-xs" @click="copyContext">📋 复制到剪贴板</button>
        </div>
        <div v-if="exportLoading" class="text-center py-10 text-slate-400">生成中…</div>
        <textarea
          v-else
          id="export-md-textarea"
          v-model="exportContextMd"
          class="w-full h-96 font-mono text-xs border border-slate-200 rounded-lg p-3 bg-slate-50 focus:bg-white focus:border-brand-400 outline-none"
          readonly
        />
        <div class="text-xs text-slate-500">
          💡 复制后到外部 AI（DeepSeek / Kimi / ChatGPT
          等）粘贴即可获得完整学情上下文。报告生成后，点下方"导入新报告"保存。
        </div>
      </div>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入 AI 报告" width="720px" top="5vh">
      <el-form label-position="top">
        <el-form-item label="报告标题" required>
          <el-input v-model="importForm.title" placeholder="如：2026 春季学期数学学情分析" maxlength="128" />
        </el-form-item>
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="来源（可选）">
            <el-input v-model="importForm.source" placeholder="如：deepseek / kimi / gpt-4o" maxlength="64" />
          </el-form-item>
          <el-form-item label="一句话摘要（可选）">
            <el-input v-model="importForm.summary" placeholder="如：数学稳步上升，语文有滑坡" maxlength="500" />
          </el-form-item>
        </div>
        <el-form-item label="AI 输出内容（markdown）" required>
          <el-input
            v-model="importForm.raw_markdown"
            type="textarea"
            :rows="14"
            placeholder="把外部 AI 给你的报告全文粘贴到这里。系统会渲染 markdown 显示。"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="importDialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submitImport">保存报告</button>
      </template>
    </el-dialog>

    <!-- 报告详情抽屉 -->
    <el-drawer v-model="activeReport" :title="activeReport?.title || '报告详情'" size="640px" direction="rtl">
      <div v-if="activeReport" class="space-y-4">
        <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span>📅 {{ dayjs(activeReport.created_at).format("YYYY-MM-DD HH:mm") }}</span>
          <span v-if="activeReport.source">· 来源 {{ activeReport.source }}</span>
        </div>
        <div
          v-if="activeReport.summary"
          class="p-3 bg-brand-50 border border-brand-100 rounded-lg text-sm text-slate-700"
        >
          💡 {{ activeReport.summary }}
        </div>
        <div class="prose prose-sm max-w-none markdown-body" v-html="renderMarkdown(activeReport.raw_markdown)"></div>
        <div class="border-t border-slate-100 pt-3 flex justify-end gap-2">
          <button
            class="btn-ghost text-sm"
            @click="
              navigator.clipboard.writeText(activeReport.raw_markdown)
              ElMessage.success('已复制原文')
            "
          >
            📋 复制原文
          </button>
          <button
            class="btn-secondary text-sm text-rose-600"
            @click="deleteReport(activeReport.id, activeReport.title)"
          >
            🗑 删除
          </button>
          <button class="btn-primary text-sm" @click="closeReport">关闭</button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.markdown-body :deep(h1) {
  font-size: 1.5rem;
  font-weight: 700;
  margin: 0.8em 0 0.5em;
  color: #1e293b;
}
.markdown-body :deep(h2) {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0.8em 0 0.4em;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.3em;
}
.markdown-body :deep(h3) {
  font-size: 1.1rem;
  font-weight: 600;
  margin: 0.7em 0 0.3em;
  color: #334155;
}
.markdown-body :deep(h4) {
  font-size: 1rem;
  font-weight: 600;
  margin: 0.6em 0 0.3em;
  color: #475569;
}
.markdown-body :deep(p) {
  margin: 0.5em 0;
  line-height: 1.7;
  color: #334155;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5em;
}
.markdown-body :deep(li) {
  margin: 0.25em 0;
  line-height: 1.6;
  color: #334155;
}
.markdown-body :deep(code) {
  background: #f1f5f9;
  padding: 0.1em 0.3em;
  border-radius: 0.25em;
  font-size: 0.9em;
  color: #be185d;
}
.markdown-body :deep(table) {
  border: 1px solid #e2e8f0;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e2e8f0;
  padding: 0.4em 0.8em;
}
.markdown-body :deep(th) {
  background: #f8fafc;
  font-weight: 600;
}
.markdown-body :deep(a) {
  color: #4f46e5;
}
</style>
