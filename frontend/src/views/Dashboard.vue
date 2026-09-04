<script setup>
import { ref, computed, onMounted, watch } from "vue"
import { useRouter } from "vue-router"
import { useChildStore } from "@/stores/child"
import api, {
  dashboardAPI,
  growthAPI,
  socialEmotionalAPI,
  interestsAPI,
  rewardsAPI,
  reportsAPI,
  questionBanksAPI,
} from "@/api"
import { ElMessage, ElMessageBox } from "element-plus"
import TrendLineChart from "@/components/charts/TrendLineChart.vue"
import RadarChart from "@/components/charts/RadarChart.vue"
import SubjectBarChart from "@/components/charts/SubjectBarChart.vue"
import dayjs from "dayjs"

const router = useRouter()
const childStore = useChildStore()
const loading = ref(false)
const dashboard = ref(null)

// 新增模块数据
const growthRecords = ref([])
const socialRecords = ref([])
const interestRecords = ref([])
// 奖励系统：积分 / 段位 / 称号
const pointsSummary = ref(null)
const ranks = ref([])
const childAchievements = ref([])
// 练习汇总（v1.8.0）
const recentExercises = ref([])

const fetchData = async () => {
  if (!childStore.currentId) return
  loading.value = true
  try {
    const [dash, growth, social, interests, achievements, points, rankList, exs] = await Promise.all([
      dashboardAPI.get(childStore.currentId),
      growthAPI.list(childStore.currentId).catch(() => []),
      socialEmotionalAPI.list(childStore.currentId).catch(() => []),
      interestsAPI.list(childStore.currentId).catch(() => []),
      rewardsAPI.childAchievements(childStore.currentId).catch(() => []),
      rewardsAPI.points(childStore.currentId).catch(() => null),
      rewardsAPI.ranks(childStore.currentId).catch(() => []),
      questionBanksAPI.listExercises(childStore.currentId).catch(() => []),
    ])
    dashboard.value = dash
    growthRecords.value = growth
    socialRecords.value = social
    interestRecords.value = interests
    childAchievements.value = achievements
    pointsSummary.value = points
    ranks.value = rankList
    recentExercises.value = Array.isArray(exs) ? exs : []
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
watch(() => childStore.currentId, fetchData)

// ============ 趋势图：科目筛选 ============
// 从 series name "数学-分数"/"数学-班均" 提取科目名
const allSubjects = computed(() => {
  const set = new Set()
  ;(dashboard.value?.trend_data?.series || []).forEach((s) => {
    const subj = (s.name || "").replace(/-(分数|班均)$/, "")
    if (subj) set.add(subj)
  })
  return Array.from(set)
})

const selectedSubjects = ref([]) // 默认空，watch 后初始化为全选
watch(
  allSubjects,
  (subs) => {
    // 首次拿到科目 / 切换 child 时，如果当前选择为空或不在新列表里，重置为全选
    const current = new Set(selectedSubjects.value)
    const next = subs.filter((s) => current.has(s))
    if (next.length === 0) selectedSubjects.value = [...subs]
    else selectedSubjects.value = next
  },
  { immediate: true },
)

const toggleSubject = (s) => {
  const has = selectedSubjects.value.includes(s)
  selectedSubjects.value = has ? selectedSubjects.value.filter((x) => x !== s) : [...selectedSubjects.value, s]
}

const selectAllSubjects = () => {
  selectedSubjects.value = [...allSubjects.value]
}

const trendChartProps = computed(() => ({
  dates: dashboard.value?.trend_data?.dates || [],
  series: (dashboard.value?.trend_data?.series || []).filter((s) => {
    const subj = (s.name || "").replace(/-(分数|班均)$/, "")
    return selectedSubjects.value.includes(subj)
  }),
}))

const radarProps = computed(() => ({
  indicators: dashboard.value?.radar_data?.indicators || [],
  values: dashboard.value?.radar_data?.values || [],
}))

const barProps = computed(() => ({
  subjects: dashboard.value?.subject_stats?.map((s) => s.subject) || [],
  avg: dashboard.value?.subject_stats?.map((s) => s.avg_score) || [],
  latest: dashboard.value?.subject_stats?.map((s) => s.latest_score) || [],
}))

// ============ 生长发育摘要 ============
const latestGrowth = computed(() => growthRecords.value[0] || null)
const growthCount = computed(() => growthRecords.value.length)
const latestVisionLeft = computed(() => latestGrowth.value?.vision_left)
const latestVisionRight = computed(() => latestGrowth.value?.vision_right)

// ============ 社交情感摘要 ============
const latestSocial = computed(() => socialRecords.value[0] || null)
const socialCount = computed(() => socialRecords.value.length)
const moodEmoji = (s) => {
  const map = { 1: "😢", 2: "😟", 3: "😐", 4: "🙂", 5: "😄" }
  return map[s] || "❓"
}

// ============ 兴趣特长摘要 ============
const latestInterests = computed(() => interestRecords.value.slice(0, 3))
const interestCount = computed(() => interestRecords.value.length)
const interestTypes = computed(() => {
  const set = new Set(interestRecords.value.map((r) => r.activity_type))
  return Array.from(set)
})

// ============ 练习汇总（v1.8.0）===========
const submittedExercises = computed(() => (recentExercises.value || []).filter((e) => e.submitted_at))
const practiceStats = computed(() => {
  const list = submittedExercises.value
  const total = list.length
  const last = list[0]
  const perfect = list.filter((e) => (e.score ?? 0) >= 80).length
  const perfectRate = total > 0 ? Math.round((perfect / total) * 100) : 0
  // 近 7 天练习次数
  const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000
  const recent7Count = list.filter((e) => new Date(e.submitted_at).getTime() >= sevenDaysAgo).length
  return { total, last, perfectRate, recent7Count }
})
const practiceScoreColor = (s) => (s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-600" : "text-rose-500")

// ============ 奖励系统摘要 ============
// 已获得的称号（按解锁时间倒序），取最近 4 个
const earnedAchievements = computed(() => (childAchievements.value || []).filter((a) => a.achievement))
const recentAchievements = computed(() => earnedAchievements.value.slice(0, 4).map((a) => a.achievement))
// 段位的中文颜色映射（王者荣耀风格）
const tierColor = (tier) => {
  const map = {
    青铜: "#8B7355",
    白银: "#C0C0C0",
    黄金: "#FFD700",
    铂金: "#00BFFF",
    钻石: "#B9F2FF",
    星耀: "#FF6B9D",
    王者: "#FF4500",
  }
  return map[tier] || "#6366f1"
}

const goAddExam = () => router.push("/exams?action=new")
const goReports = () => router.push("/ai-reports")
const goRewards = () => router.push("/rewards")

// ============ 学情周/月报（v1.7.0）===========
const periodReports = ref([])
const periodGenerating = ref(false)

async function loadPeriodReports() {
  if (!childStore.currentId) {
    periodReports.value = []
    return
  }
  try {
    periodReports.value = await reportsAPI.listPeriod(childStore.currentId)
  } catch (e) {
    // 静默忽略（首次无数据时可能 404）
  }
}

async function generatePeriod(type) {
  if (!childStore.currentId) {
    ElMessage.warning("请先选择孩子")
    return
  }
  periodGenerating.value = true
  try {
    const result = await reportsAPI.generatePeriod(childStore.currentId, { period_type: type })
    ElMessage.success(`${type === "weekly" ? "周报" : "月报"} 生成成功！${(result.file_size / 1024).toFixed(1)} KB`)
    await loadPeriodReports()
    // 自动触发下载（走 axios，拦截器自动带 Bearer 头，避免 401）
    await downloadPeriodFile(result.id)
  } catch (e) {
    ElMessage.error(`生成失败：${e?.response?.data?.detail || e.message}`)
  } finally {
    periodGenerating.value = false
  }
}

async function deletePeriod(report) {
  try {
    await ElMessageBox.confirm(
      `确认删除「${report.period_type === "weekly" ? "周报" : "月报"}」(${report.period_start} ~ ${report.period_end})？`,
      "删除报告",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    )
  } catch {
    return // 取消
  }
  try {
    await reportsAPI.deletePeriod(report.id)
    ElMessage.success("已删除")
    await loadPeriodReports()
  } catch (e) {
    ElMessage.error(`删除失败：${e?.response?.data?.detail || e.message}`)
  }
}

// 通过 axios 下载 PDF（拦截器自动带 Authorization: Bearer，解决 401 未提供登录凭证）
async function downloadPeriodFile(reportId) {
  try {
    const resp = await api.get(`/reports/period/${reportId}/download`, { responseType: "blob" })
    const cd = resp.headers["content-disposition"] || ""
    const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i)
    const filename = m ? m[1] : `ChildStudy-report-${reportId}.pdf`
    const url = window.URL.createObjectURL(new Blob([resp.data]))
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (e) {
    const detail = e?.response?.data?.detail || e.message || "未知错误"
    ElMessage.error(`下载失败：${detail}`)
  }
}

function downloadPeriod(report) {
  downloadPeriodFile(report.id)
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s} 秒`
  return `${m} 分 ${s.toString().padStart(2, "0")} 秒`
}

watch(
  () => childStore.currentId,
  () => loadPeriodReports(),
  { immediate: true },
)
</script>

<template>
  <div>
    <!-- 空态：尚未添加孩子 -->
    <div v-if="!childStore.currentId" class="card p-12 text-center">
      <div class="text-5xl mb-3">👋</div>
      <div class="text-base font-medium text-slate-600 mb-1">还没有添加孩子档案</div>
      <div class="text-sm text-slate-400 mb-5">先添加一个孩子，才能开始记录学习、生长与成长数据</div>
      <button class="btn-primary" @click="router.push('/children')">前往添加</button>
    </div>

    <div v-else-if="loading" class="flex items-center justify-center py-20 text-slate-400 gap-2">
      <span class="inline-block w-5 h-5 border-2 border-slate-300 border-t-brand-600 rounded-full animate-spin"></span>
      <span class="text-sm">看板加载中…</span>
    </div>

    <div v-else-if="dashboard" class="space-y-5">
      <!-- 顶部欢迎横幅 -->
      <div class="card p-5">
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div class="flex items-center gap-3">
            <span
              class="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white text-xl shadow-sm"
              >📊</span
            >
            <div>
              <div class="text-xs text-slate-500">{{ childStore.current?.grade }}</div>
              <h2 class="text-xl font-semibold text-slate-800 mt-0.5">{{ dashboard.child_name }} 的学习看板</h2>
              <p class="text-xs text-slate-400 mt-0.5">考试、作业、练习、成就与成长一站式掌握</p>
            </div>
          </div>
          <div class="flex gap-2">
            <button class="btn-secondary" @click="router.push('/children')">管理档案</button>
            <button class="btn-primary" @click="goAddExam">+ 录入考试</button>
          </div>
        </div>

        <!-- 顶部四联卡：统计 -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
          <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-brand-400 to-brand-600"></div>
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-brand-50 text-brand-600 text-base"
                >📝</span
              >
              <span class="text-xs text-slate-500">累计考试</span>
            </div>
            <div class="mt-2 flex items-baseline gap-1">
              <span class="text-2xl font-bold text-slate-800">{{ dashboard.total_exams }}</span>
              <span class="text-xs text-slate-400 font-medium">次</span>
            </div>
            <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">已有记录的考试场次</div>
          </div>
          <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-400 to-indigo-600"></div>
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 text-base"
                >📚</span
              >
              <span class="text-xs text-slate-500">作业记录</span>
            </div>
            <div class="mt-2 flex items-baseline gap-1">
              <span class="text-2xl font-bold text-slate-800">{{ dashboard.total_homeworks }}</span>
              <span class="text-xs text-slate-400 font-medium">项</span>
            </div>
            <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">已记录的作业条目</div>
          </div>
          <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-amber-400 to-amber-600"></div>
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-amber-50 text-amber-600 text-base"
                >🎯</span
              >
              <span class="text-xs text-slate-500">薄弱科目</span>
            </div>
            <div class="mt-2 flex items-baseline gap-1">
              <span
                v-if="dashboard.weak_subjects.length"
                class="text-base font-semibold text-amber-700 leading-tight"
                >{{ dashboard.weak_subjects.join("、") }}</span
              >
              <span v-else class="text-base font-medium text-emerald-600 leading-tight">暂无明显薄弱</span>
            </div>
            <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">建议重点关注</div>
          </div>
          <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
            <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 to-emerald-600"></div>
            <div class="flex items-center gap-2">
              <span
                class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 text-base"
                >🏅</span
              >
              <span class="text-xs text-slate-500">最近考试</span>
            </div>
            <div class="mt-2 flex items-baseline gap-1">
              <span v-if="dashboard.recent_exams[0]" class="text-lg font-semibold text-slate-800 leading-tight">
                {{ dashboard.recent_exams[0].subject }}
              </span>
              <span v-else class="text-base font-medium text-slate-400 leading-tight">暂无</span>
            </div>
            <div
              v-if="dashboard.recent_exams[0]"
              class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400"
            >
              得分率
              <span class="font-semibold text-emerald-600"
                >{{ Math.round((dashboard.recent_exams[0].score / dashboard.recent_exams[0].full_score) * 100) }}%</span
              >
            </div>
            <div v-else class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">去录入第一条考试</div>
          </div>
        </div>
      </div>

      <!-- ✏️ 练习汇总（v1.8.0） -->
      <div v-if="practiceStats.total > 0" class="card overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-indigo-50/80 to-transparent flex items-center justify-between flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-indigo-500">✏️</span>
            <span class="text-sm font-semibold text-slate-800">练习情况</span>
          </div>
          <button class="btn-ghost text-xs" @click="router.push('/question-banks')">查看题库 →</button>
        </div>
        <div class="p-4">
          <!-- 顶部四联卡：总次数 / 近7天 / 最近得分 / 优秀率 -->
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-indigo-400 to-indigo-600"></div>
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 text-base"
                  >🏋️</span
                >
                <span class="text-xs text-slate-500">总练习次数</span>
              </div>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-2xl font-bold text-indigo-800">{{ practiceStats.total }}</span>
                <span class="text-xs text-slate-400 font-medium">次</span>
              </div>
              <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">累计提交练习</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-sky-400 to-sky-600"></div>
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-sky-50 text-sky-600 text-base"
                  >🔥</span
                >
                <span class="text-xs text-slate-500">近 7 天</span>
              </div>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-2xl font-bold text-slate-800">{{ practiceStats.recent7Count }}</span>
                <span class="text-xs text-slate-400 font-medium">次</span>
              </div>
              <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">本周练习节奏</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-violet-400 to-violet-600"></div>
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-violet-50 text-violet-600 text-base"
                  >🎯</span
                >
                <span class="text-xs text-slate-500">最近得分</span>
              </div>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-2xl font-bold" :class="practiceScoreColor(practiceStats.last?.score || 0)">
                  {{ practiceStats.last?.score?.toFixed?.(1) ?? practiceStats.last?.score ?? 0 }}
                </span>
                <span class="text-xs text-slate-400 font-medium">分</span>
              </div>
              <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400 truncate">
                {{ practiceStats.last?.bank_title || "—" }}
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-4 relative overflow-hidden border border-slate-100">
              <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 to-emerald-600"></div>
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 text-base"
                  >🌟</span
                >
                <span class="text-xs text-slate-500">优秀率 (≥80%)</span>
              </div>
              <div class="mt-2 flex items-baseline gap-1">
                <span class="text-2xl font-bold text-emerald-700">{{ practiceStats.perfectRate }}</span>
                <span class="text-xs text-slate-400 font-medium">%</span>
              </div>
              <div class="mt-2 pt-2 border-t border-slate-100 text-[11px] text-slate-400">达优秀线比例</div>
            </div>
          </div>

          <!-- 最近 5 次列表 -->
          <div class="text-xs text-slate-500 mb-2">最近 5 次：</div>
          <div class="space-y-2">
            <div
              v-for="e in submittedExercises.slice(0, 5)"
              :key="e.id"
              class="flex items-center justify-between p-2.5 rounded-lg bg-slate-50/60 hover:bg-slate-50 transition-colors"
            >
              <div class="min-w-0 flex-1">
                <div class="text-sm font-medium text-slate-700 truncate">
                  {{ e.bank_title || `题库 #${e.bank_id}` }}
                </div>
                <div class="text-xs text-slate-400 mt-0.5">
                  {{ dayjs.utc(e.submitted_at).tz("Asia/Shanghai").format("MM-DD HH:mm:ss") }}
                  <span class="mx-1">·</span>
                  答对 {{ e.correct_count }}/{{ e.total_questions }}
                  <span v-if="e.time_spent" class="mx-1">·</span>
                  <span v-if="e.time_spent">用时 {{ formatDuration(e.time_spent) }}</span>
                </div>
              </div>
              <span class="text-base font-semibold ml-3" :class="practiceScoreColor(e.score || 0)">
                {{ (e.score ?? 0).toFixed(1) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 趋势图 + 雷达 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div class="card p-5 lg:col-span-2">
          <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 class="font-semibold text-slate-800">成绩趋势</h3>
            <div class="flex items-center gap-1.5 flex-wrap">
              <span class="text-xs text-slate-400 mr-1">筛选科目：</span>
              <button
                v-for="s in allSubjects"
                :key="s"
                type="button"
                :class="[
                  'px-2.5 py-0.5 rounded-full text-xs border transition select-none',
                  selectedSubjects.includes(s)
                    ? 'bg-brand-500 text-white border-brand-500 shadow-sm'
                    : 'bg-white text-slate-500 border-slate-200 hover:border-brand-300 hover:bg-brand-50',
                ]"
                @click="toggleSubject(s)"
              >
                {{ s }}
              </button>
              <button
                v-if="selectedSubjects.length !== allSubjects.length"
                type="button"
                class="text-xs text-brand-600 hover:underline ml-1.5"
                @click="selectAllSubjects"
              >
                全选
              </button>
              <span class="text-xs text-slate-400 ml-1.5">按考试日期</span>
            </div>
          </div>
          <TrendLineChart v-if="trendChartProps.dates.length" v-bind="trendChartProps" height="300px" />
          <div
            v-else-if="allSubjects.length === 0"
            class="h-64 flex items-center justify-center text-slate-400 text-sm"
          >
            还没有考试数据，去录入第一条吧
          </div>
          <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">请至少勾选一个科目</div>
        </div>

        <div class="card p-5">
          <RadarChart v-if="radarProps.indicators.length" v-bind="radarProps" title="能力分布" />
          <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">录入数据后查看</div>
        </div>
      </div>

      <!-- 科目对比 + 近期考试 -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div class="card p-5 lg:col-span-2">
          <h3 class="font-semibold text-slate-800 mb-3">科目对比</h3>
          <SubjectBarChart v-if="barProps.subjects.length" v-bind="barProps" />
          <div v-else class="h-60 flex items-center justify-center text-slate-400 text-sm">暂无数据</div>
        </div>

        <div class="card p-5">
          <h3 class="font-semibold text-slate-800 mb-3">最近考试</h3>
          <div v-if="dashboard.recent_exams.length === 0" class="text-sm text-slate-400 py-6 text-center">暂无记录</div>
          <div v-else class="space-y-2">
            <div
              v-for="e in dashboard.recent_exams.slice(0, 5)"
              :key="e.id"
              class="flex items-center justify-between p-2.5 rounded-lg hover:bg-slate-50"
            >
              <div class="min-w-0">
                <div class="text-sm font-medium text-slate-700 truncate">{{ e.exam_name }}</div>
                <div class="text-xs text-slate-400 mt-0.5">
                  {{ e.subject }} · {{ dayjs.utc(e.exam_date).tz("Asia/Shanghai").format("MM-DD") }}
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0">
                <span class="text-sm font-semibold text-slate-800">
                  {{ Math.round((e.score / e.full_score) * 100) }}%
                </span>
                <span
                  v-if="e.target_score != null"
                  class="text-[10px] px-1.5 py-0.5 rounded-full"
                  :class="e.score >= e.target_score ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
                >
                  目标 {{ e.target_score }}
                </span>
                <span class="text-xs text-slate-400">{{ e.score }}/{{ e.full_score }}</span>
              </div>
            </div>
          </div>
          <button
            v-if="dashboard.recent_exams.length"
            class="btn-ghost w-full mt-3 text-xs"
            @click="router.push('/exams')"
          >
            查看全部 →
          </button>
        </div>
      </div>

      <!-- AI 入口 -->
      <div class="card p-5 bg-gradient-to-r from-brand-500 to-brand-700 text-white border-0">
        <div class="flex items-center justify-between flex-wrap gap-3">
          <div>
            <div class="text-sm opacity-90">AI 报告管理</div>
            <div class="font-semibold text-lg mt-0.5">用外部 AI 分析，把报告粘回系统留存</div>
          </div>
          <button class="bg-white text-brand-700 hover:bg-brand-50 btn" @click="goReports">管理 AI 报告 →</button>
        </div>
      </div>

      <!-- 📑 学情周报/月报（v1.7.0） -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div>
            <h3 class="font-semibold text-slate-800 flex items-center gap-2">📑 学情周报/月报</h3>
            <p class="text-xs text-slate-500 mt-0.5">
              系统自动聚合考试/错题/KP/段位/积分，导出 PDF（中文渲染·本地生成·隐私零泄露）
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="btn-secondary text-sm"
              :disabled="periodGenerating || !childStore.currentId"
              @click="generatePeriod('weekly')"
            >
              <span v-if="periodGenerating">生成中…</span>
              <span v-else>📅 生成本周周报</span>
            </button>
            <button
              class="btn-primary text-sm"
              :disabled="periodGenerating || !childStore.currentId"
              @click="generatePeriod('monthly')"
            >
              <span v-if="periodGenerating">生成中…</span>
              <span v-else>🗓 生成本月月报</span>
            </button>
          </div>
        </div>

        <div v-if="!childStore.currentId" class="text-sm text-slate-400 py-6 text-center">请先选择孩子</div>
        <div v-else-if="periodReports.length === 0" class="text-sm text-slate-400 py-6 text-center">
          还没有生成过报告，点上方按钮一键生成
        </div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-slate-500 border-b border-slate-200">
                <th class="py-2 pr-3">类型</th>
                <th class="py-2 pr-3">周期</th>
                <th class="py-2 pr-3">生成时间</th>
                <th class="py-2 pr-3">大小</th>
                <th class="py-2 pr-3 text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in periodReports" :key="r.id" class="border-b border-slate-100 hover:bg-slate-50">
                <td class="py-2.5 pr-3">
                  <span
                    class="px-2 py-0.5 rounded-full text-xs font-medium"
                    :class="r.period_type === 'weekly' ? 'bg-indigo-50 text-indigo-700' : 'bg-amber-50 text-amber-700'"
                  >
                    {{ r.period_type === "weekly" ? "周报" : "月报" }}
                  </span>
                </td>
                <td class="py-2.5 pr-3 text-slate-600">{{ r.period_start }} ~ {{ r.period_end }}</td>
                <td class="py-2.5 pr-3 text-slate-600">
                  {{ dayjs.utc(r.created_at).tz("Asia/Shanghai").format("MM-DD HH:mm") }}
                </td>
                <td class="py-2.5 pr-3 text-slate-600">{{ (r.file_size / 1024).toFixed(1) }} KB</td>
                <td class="py-2.5 pr-3 text-right">
                  <button class="text-indigo-600 hover:text-indigo-800 text-xs mr-3" @click="downloadPeriod(r)">
                    ⬇️ 下载
                  </button>
                  <button class="text-rose-500 hover:text-rose-700 text-xs" @click="deletePeriod(r)">🗑 删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 🏆 学习成就（积分 + 段位 + 称号） -->
      <div v-if="pointsSummary || ranks.length" class="card overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-amber-50/80 to-transparent flex items-center justify-between flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-amber-500">🏆</span>
            <span class="text-sm font-semibold text-slate-800">学习成就</span>
          </div>
          <button class="btn-ghost text-xs" @click="goRewards">查看详情 →</button>
        </div>
        <div class="p-4">
          <!-- 顶部三联卡：总积分 / 已获称号 / 段位数 -->
          <div class="grid grid-cols-3 gap-3 mb-4">
            <div
              class="bg-gradient-to-br from-brand-500 to-brand-700 rounded-xl p-3.5 text-white shadow-sm relative overflow-hidden"
            >
              <span class="absolute -right-2 -top-2 w-14 h-14 rounded-full bg-white/10"></span>
              <div class="text-xs opacity-90">总积分</div>
              <div class="text-3xl font-bold mt-0.5 leading-tight">{{ pointsSummary?.total ?? 0 }}</div>
              <div class="text-[10px] opacity-80 mt-1">
                获得 {{ pointsSummary?.earned ?? 0 }} · 消费 {{ pointsSummary?.spent ?? 0 }}
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3.5 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-amber-50 text-amber-500 text-xs"
                  >🏅</span
                >
                <span class="text-xs text-slate-500">已获称号</span>
              </div>
              <div class="text-3xl font-bold text-slate-800 mt-1 leading-tight">{{ earnedAchievements.length }}</div>
              <div class="text-[10px] text-slate-400 mt-1">继续努力解锁更多</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3.5 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-6 h-6 rounded-lg bg-violet-50 text-violet-500 text-xs"
                  >🥇</span
                >
                <span class="text-xs text-slate-500">科目段位</span>
              </div>
              <div class="text-3xl font-bold text-slate-800 mt-1 leading-tight">{{ ranks.length }}</div>
              <div class="text-[10px] text-slate-400 mt-1">按科目独立计算</div>
            </div>
          </div>

          <!-- 段位 chips（按科目独立显示，联考王者那种味儿） -->
          <div v-if="ranks.length" class="mb-3">
            <div class="text-xs text-slate-500 mb-2">科目段位：</div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="r in ranks"
                :key="r.subject"
                class="flex items-center gap-1.5 px-3 py-1 rounded-lg text-sm font-medium"
                :style="{
                  backgroundColor: tierColor(r.tier) + '22',
                  color: tierColor(r.tier),
                  border: '1px solid ' + tierColor(r.tier),
                }"
              >
                <span>{{ r.subject }}</span>
                <span class="opacity-50">·</span>
                <span class="font-semibold">{{ r.tier }}</span>
                <span class="text-[10px] opacity-70 ml-1">{{ Math.round(r.avg_score) }}分</span>
              </div>
            </div>
          </div>

          <!-- 最近获得的称号 -->
          <div v-if="recentAchievements.length">
            <div class="text-xs text-slate-500 mb-2">最近获得称号：</div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="a in recentAchievements"
                :key="a.id"
                class="px-3 py-1.5 rounded-lg bg-amber-50/70 flex items-center gap-1.5 border border-amber-100"
              >
                <span class="text-sm font-medium text-slate-700">{{ a.name }}</span>
              </div>
            </div>
          </div>
          <div v-else-if="ranks.length" class="text-sm text-slate-400 text-center py-3 bg-slate-50/60 rounded-lg">
            还没有获得称号，继续努力解锁第一个吧 🎯
          </div>
        </div>
      </div>

      <!-- 生长发育 -->
      <div v-if="growthCount" class="card overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-brand-50/70 to-transparent flex items-center justify-between flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-brand-600">📏</span>
            <span class="text-sm font-semibold text-slate-800">生长发育</span>
          </div>
          <button class="btn-ghost text-xs" @click="router.push('/growth')">查看详情 →</button>
        </div>
        <div class="p-4">
          <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-brand-50 text-brand-600 text-sm"
                  >📏</span
                >
                <span class="text-[11px] text-slate-500">最新身高</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">
                {{ latestGrowth?.height_cm ? latestGrowth.height_cm + " cm" : "-" }}
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 text-sm"
                  >⚖️</span
                >
                <span class="text-[11px] text-slate-500">最新体重</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">
                {{ latestGrowth?.weight_kg ? latestGrowth.weight_kg + " kg" : "-" }}
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-violet-50 text-violet-600 text-sm"
                  >🧮</span
                >
                <span class="text-[11px] text-slate-500">BMI</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">{{ latestGrowth?.bmi ?? "-" }}</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-sky-50 text-sky-600 text-sm"
                  >👁️</span
                >
                <span class="text-[11px] text-slate-500">左眼视力</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">{{ latestVisionLeft ?? "-" }}</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-teal-50 text-teal-600 text-sm"
                  >👁️</span
                >
                <span class="text-[11px] text-slate-500">右眼视力</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">{{ latestVisionRight ?? "-" }}</div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-amber-50 text-amber-600 text-sm"
                  >🗓️</span
                >
                <span class="text-[11px] text-slate-500">记录次数</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">
                {{ growthCount }} <span class="text-xs font-medium text-slate-400">次</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 社交情感 -->
      <div v-if="socialCount" class="card overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-brand-50/70 to-transparent flex items-center justify-between flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-brand-600">💭</span>
            <span class="text-sm font-semibold text-slate-800">社交情感</span>
          </div>
          <button class="btn-ghost text-xs" @click="router.push('/social-emotional')">查看详情 →</button>
        </div>
        <div class="p-4">
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div class="bg-slate-50/70 rounded-xl p-3.5 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-rose-50 text-rose-500 text-sm"
                  >😊</span
                >
                <span class="text-[11px] text-slate-500">当前情绪</span>
              </div>
              <div class="mt-1.5 flex items-center gap-1.5">
                <span class="text-2xl">{{ moodEmoji(latestSocial?.mood_score) }}</span>
                <span class="text-xs text-slate-400">{{
                  latestSocial?.mood_score ? latestSocial.mood_score + "/5" : "-"
                }}</span>
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3.5 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-indigo-50 text-indigo-500 text-sm"
                  >💪</span
                >
                <span class="text-[11px] text-slate-500">自信心</span>
              </div>
              <div class="mt-1.5 text-lg font-bold text-slate-800">
                {{ latestSocial?.confidence_level ? latestSocial.confidence_level + "/5" : "-" }}
              </div>
            </div>
            <div class="bg-slate-50/70 rounded-xl p-3.5 relative overflow-hidden border border-slate-100">
              <div class="flex items-center gap-2">
                <span
                  class="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-brand-50 text-brand-600 text-sm"
                  >🏷️</span
                >
                <span class="text-[11px] text-slate-500">最近情绪标签</span>
              </div>
              <div class="flex flex-wrap gap-1 mt-1.5">
                <span
                  v-for="tag in latestSocial?.emotion_tags || []"
                  :key="tag"
                  class="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-700"
                  >{{ tag }}</span
                >
                <span v-if="!latestSocial?.emotion_tags?.length" class="text-xs text-slate-400">-</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 兴趣特长 -->
      <div v-if="interestCount" class="card overflow-hidden">
        <div
          class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-brand-50/70 to-transparent flex items-center justify-between flex-wrap gap-2"
        >
          <div class="flex items-center gap-2">
            <span class="text-brand-600">🎨</span>
            <span class="text-sm font-semibold text-slate-800">兴趣特长</span>
          </div>
          <button class="btn-ghost text-xs" @click="router.push('/interests')">查看详情 →</button>
        </div>
        <div class="p-4">
          <div class="flex flex-wrap gap-2 mb-3">
            <span v-for="t in interestTypes" :key="t" class="text-xs px-2 py-1 rounded-lg bg-brand-50 text-brand-700">{{
              t
            }}</span>
          </div>
          <div class="space-y-2">
            <div
              v-for="r in latestInterests"
              :key="r.id"
              class="flex items-center justify-between p-2.5 rounded-lg bg-slate-50/60 border border-slate-100/70"
            >
              <div>
                <span class="text-sm font-medium text-slate-700">{{ r.activity_name }}</span>
                <span class="text-xs text-slate-400 ml-2">{{ r.record_date }}</span>
              </div>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-600">{{ r.skill_level }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
