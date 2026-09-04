<script setup>
import { ref, computed, onMounted } from "vue"
import { useAuthStore } from "@/stores/auth"
import { rewardsAPI, wrongQuestionsAPI, dashboardAPI, questionBanksAPI, quoteAPI } from "@/api"
import dayjs from "dayjs"
import TrendLineChart from "@/components/charts/TrendLineChart.vue"
import RadarChart from "@/components/charts/RadarChart.vue"

const auth = useAuthStore()

const childId = computed(() => auth.currentChildId)
const displayName = computed(() => auth.user?.display_name || "同学")

const loading = ref(true)
const points = ref({ earned: 0, spent: 0 })
const achievementCount = ref(0)
const wrongStats = ref({ total: 0, active: 0, mastered: 0 })
const dashboard = ref(null)
// 练习汇总（v1.8.0）
const recentExercises = ref([])

// 随机诗词 / 名言（欢迎栏展示，点击可换一条）
const quote = ref(null)
const quoteLoading = ref(false)

async function loadQuote() {
  if (quoteLoading.value) return
  quoteLoading.value = true
  try {
    quote.value = await quoteAPI.random()
  } catch (e) {
    // 接口异常时静默，卡片不显示即可
  } finally {
    quoteLoading.value = false
  }
}

const availablePoints = computed(() => (points.value.earned || 0) - (points.value.spent || 0))

// 练习汇总：总次数 / 最近一次 / 完美率（>=80%）
const practiceStats = computed(() => {
  const list = (recentExercises.value || []).filter((e) => e.submitted_at)
  const total = list.length
  const last = list[0]
  const perfect = list.filter((e) => (e.score ?? 0) >= 80).length
  const perfectRate = total > 0 ? Math.round((perfect / total) * 100) : 0
  return { total, last, perfectRate }
})

const scoreColor = (s) => (s >= 80 ? "text-emerald-600" : s >= 60 ? "text-amber-600" : "text-rose-500")

// 成绩曲线（家长看板 dashboardAPI.get 返回的 trend_data）
const trendChartProps = computed(() => ({
  dates: dashboard.value?.trend_data?.dates || [],
  series: dashboard.value?.trend_data?.series || [],
}))

// 五边形能力图（radar_data）
const radarProps = computed(() => ({
  indicators: dashboard.value?.radar_data?.indicators || [],
  values: dashboard.value?.radar_data?.values || [],
}))

const quickLinks = [
  { name: "wrong-questions", path: "/wrong-questions", label: "错题本", icon: "📙", desc: "复习我的错题" },
  { name: "rewards", path: "/rewards", label: "奖励商城", icon: "🎁", desc: "用积分换奖品" },
  { name: "achievements", path: "/achievements", label: "成就墙", icon: "🏆", desc: "看看我获得的成就" },
  { name: "study-progress", path: "/study-progress", label: "教材学习进度", icon: "📚", desc: "学到第几课啦" },
  { name: "project-works", path: "/project-works", label: "单元 Big Task", icon: "🎨", desc: "我的作品集" },
  { name: "question-banks", path: "/question-banks", label: "题库练习", icon: "✏️", desc: "来做几道题" },
]

async function load() {
  if (!childId.value) return
  loading.value = true
  try {
    const [p, ach, ws, dash, exs] = await Promise.all([
      rewardsAPI.points(childId.value),
      rewardsAPI.childAchievements(childId.value),
      wrongQuestionsAPI.stats(childId.value),
      dashboardAPI.get(childId.value),
      questionBanksAPI.listExercises(childId.value).catch(() => []),
    ])
    points.value = p || { earned: 0, spent: 0 }
    achievementCount.value = Array.isArray(ach) ? ach.length : 0
    wrongStats.value = ws || { total: 0, active: 0, mastered: 0 }
    dashboard.value = dash || null
    recentExercises.value = Array.isArray(exs) ? exs : []
  } catch (e) {
    // 静默失败，模板已做防御渲染
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  loadQuote()
})

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m === 0) return `${s} 秒`
  return `${m} 分 ${s.toString().padStart(2, "0")} 秒`
}
</script>

<template>
  <div class="space-y-6">
    <!-- 欢迎 -->
    <div class="bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl px-6 py-7 text-white shadow-sm">
      <div class="flex flex-col sm:flex-row sm:items-center gap-4">
        <!-- 左：问候语 -->
        <div class="shrink-0">
          <div class="text-sm opacity-80">我的看板</div>
          <div class="text-2xl font-semibold mt-1">👋 你好，{{ displayName }}！</div>
          <div class="text-sm opacity-80 mt-1">这是专属于你的成长空间</div>
        </div>
        <!-- 右：随机诗词 / 名言（点击换一条） -->
        <button
          v-if="quote"
          class="quote-banner w-full sm:ml-auto sm:max-w-sm text-left rounded-xl bg-white/10 border border-white/15 px-4 py-3 hover:bg-white/15 active:scale-[0.98] transition-all"
          :disabled="quoteLoading"
          title="点一下换一句"
          @click="loadQuote"
        >
          <div class="flex items-start gap-2">
            <span class="quote-mark text-xl leading-none select-none opacity-60">「</span>
            <div class="min-w-0 flex-1">
              <p class="text-[13px] leading-relaxed font-medium" :class="{ 'opacity-60': quoteLoading }">
                {{ quote.content }}
              </p>
              <p class="text-[11px] opacity-75 mt-1">
                —— {{ quote.author }}<template v-if="quote.source"> · {{ quote.source }}</template>
              </p>
            </div>
            <span class="text-sm opacity-60 select-none shrink-0 mt-0.5" :class="{ 'animate-spin': quoteLoading }"
              >⟳</span
            >
          </div>
        </button>
      </div>
    </div>

    <!-- 统计卡片（可点击跳转，适配触摸屏） -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <router-link to="/rewards" class="stat-card group">
        <div class="flex items-center justify-between">
          <div class="text-xs text-slate-400">可用积分</div>
          <span class="text-slate-300 group-hover:text-amber-400 transition-colors text-sm">→</span>
        </div>
        <div class="text-2xl font-bold text-amber-500 mt-1">
          {{ loading ? "…" : availablePoints }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">累计获得 {{ points.earned || 0 }} · 去商城逛逛</div>
      </router-link>
      <router-link to="/achievements" class="stat-card group">
        <div class="flex items-center justify-between">
          <div class="text-xs text-slate-400">我的成就</div>
          <span class="text-slate-300 group-hover:text-brand-500 transition-colors text-sm">→</span>
        </div>
        <div class="text-2xl font-bold text-brand-600 mt-1">
          {{ loading ? "…" : achievementCount }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">枚勋章已点亮 · 看看成就墙</div>
      </router-link>
      <router-link to="/wrong-questions" class="stat-card group">
        <div class="flex items-center justify-between">
          <div class="text-xs text-slate-400">待复习错题</div>
          <span class="text-slate-300 group-hover:text-rose-400 transition-colors text-sm">→</span>
        </div>
        <div class="text-2xl font-bold text-rose-500 mt-1">
          {{ loading ? "…" : wrongStats.active || 0 }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">共 {{ wrongStats.total || 0 }} 道 · 去复习</div>
      </router-link>
    </div>

    <!-- ✏️ 练习情况（v1.8.0） -->
    <div v-if="practiceStats.total > 0" class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 class="font-semibold text-slate-800 flex items-center gap-2">✏️ 我的练习</h3>
        <router-link to="/question-banks" class="text-xs text-brand-600 hover:text-brand-700 hover:underline"
          >去练习 →</router-link
        >
      </div>

      <!-- 顶部三联卡：总次数 / 最近得分 / 优秀率 -->
      <div class="grid grid-cols-3 gap-3 mb-4">
        <div class="bg-indigo-50 rounded-lg p-3.5">
          <div class="text-xs text-indigo-700">总练习次数</div>
          <div class="text-2xl font-bold text-indigo-800 mt-1">{{ practiceStats.total }}</div>
          <div class="text-[10px] text-indigo-600 mt-1">提交记录</div>
        </div>
        <div class="bg-slate-50 rounded-lg p-3.5">
          <div class="text-xs text-slate-500">最近得分</div>
          <div class="text-2xl font-bold mt-1" :class="scoreColor(practiceStats.last?.score || 0)">
            {{ practiceStats.last?.score?.toFixed?.(1) ?? practiceStats.last?.score ?? 0 }}
          </div>
          <div class="text-[10px] text-slate-400 mt-1 truncate">{{ practiceStats.last?.bank_title || "—" }}</div>
        </div>
        <div class="bg-emerald-50 rounded-lg p-3.5">
          <div class="text-xs text-emerald-700">优秀率 (≥80%)</div>
          <div class="text-2xl font-bold text-emerald-800 mt-1">{{ practiceStats.perfectRate }}%</div>
          <div class="text-[10px] text-emerald-600 mt-1">继续保持 →</div>
        </div>
      </div>

      <!-- 最近 5 次练习 -->
      <div class="text-xs text-slate-500 mb-2">最近 5 次：</div>
      <div class="space-y-2">
        <div
          v-for="e in recentExercises.slice(0, 5)"
          :key="e.id"
          class="flex items-center justify-between p-2.5 rounded-lg bg-slate-50/70 hover:bg-slate-100 transition-colors"
        >
          <div class="min-w-0 flex-1">
            <div class="text-sm font-medium text-slate-700 truncate">{{ e.bank_title || `题库 #${e.bank_id}` }}</div>
            <div class="text-xs text-slate-400 mt-0.5">
              {{
                dayjs
                  .utc(e.submitted_at || e.created_at)
                  .tz("Asia/Shanghai")
                  .format("MM-DD HH:mm:ss")
              }}
              <span class="mx-1">·</span>
              答对 {{ e.correct_count }}/{{ e.total_questions }}
              <span v-if="e.time_spent" class="mx-1">·</span>
              <span v-if="e.time_spent">用时 {{ formatDuration(e.time_spent) }}</span>
            </div>
          </div>
          <span class="text-base font-semibold ml-3" :class="scoreColor(e.score || 0)">
            {{ (e.score ?? 0).toFixed(1) }}
          </span>
        </div>
      </div>
    </div>

    <!-- 成绩趋势 + 能力分布（五边形） -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm lg:col-span-2">
        <h3 class="font-semibold text-slate-800 mb-3">📈 成绩趋势</h3>
        <TrendLineChart v-if="trendChartProps.dates.length" v-bind="trendChartProps" height="300px" />
        <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">
          还没有考试数据，去练习一下吧
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 class="font-semibold text-slate-800 mb-3">🕸️ 能力分布</h3>
        <RadarChart v-if="radarProps.indicators.length" v-bind="radarProps" title="能力分布" />
        <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">录入成绩后查看</div>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div>
      <div class="text-sm font-semibold text-slate-500 mb-3">去逛逛</div>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <router-link
          v-for="q in quickLinks"
          :key="q.name"
          :to="q.path"
          class="flex items-center gap-3 bg-white rounded-xl border border-slate-200 px-4 py-4 shadow-sm hover:border-brand-300 hover:shadow transition-all"
        >
          <span class="text-2xl">{{ q.icon }}</span>
          <div class="min-w-0">
            <div class="text-sm font-semibold text-slate-700">{{ q.label }}</div>
            <div class="text-[11px] text-slate-400 truncate">{{ q.desc }}</div>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 可点击统计卡：触摸屏友好 */
.stat-card {
  display: block;
  background: white;
  border-radius: 0.75rem;
  border: 1px solid #e2e8f0;
  padding: 1rem 1.25rem;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.05);
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent; /* 去掉 pad 上的蓝色点按高亮 */
  touch-action: manipulation; /* 消除移动端 300ms 点击延迟 */
  transition:
    transform 0.12s ease,
    box-shadow 0.15s ease,
    border-color 0.15s ease;
}
.stat-card:hover {
  border-color: #c7d2fe;
  box-shadow: 0 4px 12px rgb(0 0 0 / 0.08);
}
.stat-card:active {
  transform: scale(0.97); /* 手指按下的即时反馈 */
}
.stat-card:focus-visible {
  outline: 2px solid #6366f1;
  outline-offset: 2px;
}

/* 随机诗词 / 名言横幅：触摸屏友好 */
.quote-banner {
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}
.quote-banner p {
  font-family: "Noto Serif SC", "Songti SC", "STSong", "SimSun", serif; /* 诗句用衬线字体更有韵味 */
}
.quote-mark {
  font-family: "Noto Serif SC", "Songti SC", "STSong", "SimSun", serif;
}
</style>
