<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { rewardsAPI, wrongQuestionsAPI, dashboardAPI } from "@/api";
import TrendLineChart from "@/components/charts/TrendLineChart.vue";
import RadarChart from "@/components/charts/RadarChart.vue";

const auth = useAuthStore();
const router = useRouter();

const childId = computed(() => auth.currentChildId);
const displayName = computed(() => auth.user?.display_name || "同学");

const loading = ref(true);
const points = ref({ earned: 0, spent: 0 });
const achievementCount = ref(0);
const wrongStats = ref({ total: 0, active: 0, mastered: 0 });
const dashboard = ref(null);

const availablePoints = computed(() => (points.value.earned || 0) - (points.value.spent || 0));

// 成绩曲线（家长看板 dashboardAPI.get 返回的 trend_data）
const trendChartProps = computed(() => ({
  dates: dashboard.value?.trend_data?.dates || [],
  series: dashboard.value?.trend_data?.series || [],
}));

// 五边形能力图（radar_data）
const radarProps = computed(() => ({
  indicators: dashboard.value?.radar_data?.indicators || [],
  values: dashboard.value?.radar_data?.values || [],
}));

const quickLinks = [
  { name: "wrong-questions", path: "/wrong-questions", label: "错题本", icon: "📙", desc: "复习我的错题" },
  { name: "rewards", path: "/rewards", label: "奖励商城", icon: "🎁", desc: "用积分换奖品" },
  { name: "achievements", path: "/achievements", label: "成就墙", icon: "🏆", desc: "看看我获得的成就" },
  { name: "study-progress", path: "/study-progress", label: "教材学习进度", icon: "📚", desc: "学到第几课啦" },
  { name: "project-works", path: "/project-works", label: "单元 Big Task", icon: "🎨", desc: "我的作品集" },
  { name: "question-banks", path: "/question-banks", label: "题库练习", icon: "✏️", desc: "来做几道题" },
];

async function load() {
  if (!childId.value) return;
  loading.value = true;
  try {
    const [p, ach, ws, dash] = await Promise.all([
      rewardsAPI.points(childId.value),
      rewardsAPI.childAchievements(childId.value),
      wrongQuestionsAPI.stats(childId.value),
      dashboardAPI.get(childId.value),
    ]);
    points.value = p || { earned: 0, spent: 0 };
    achievementCount.value = Array.isArray(ach) ? ach.length : 0;
    wrongStats.value = ws || { total: 0, active: 0, mastered: 0 };
    dashboard.value = dash || null;
  } catch (e) {
    // 静默失败，模板已做防御渲染
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<template>
  <div class="space-y-6">
    <!-- 欢迎 -->
    <div class="bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl px-6 py-7 text-white shadow-sm">
      <div class="text-sm opacity-80">我的看板</div>
      <div class="text-2xl font-semibold mt-1">👋 你好，{{ displayName }}！</div>
      <div class="text-sm opacity-80 mt-1">这是专属于你的成长空间</div>
    </div>

    <!-- 统计卡片 -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white rounded-xl border border-slate-200 px-5 py-4 shadow-sm">
        <div class="text-xs text-slate-400">可用积分</div>
        <div class="text-2xl font-bold text-amber-500 mt-1">
          {{ loading ? "…" : availablePoints }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">累计获得 {{ points.earned || 0 }}</div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 px-5 py-4 shadow-sm">
        <div class="text-xs text-slate-400">我的成就</div>
        <div class="text-2xl font-bold text-brand-600 mt-1">
          {{ loading ? "…" : achievementCount }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">枚勋章已点亮</div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 px-5 py-4 shadow-sm">
        <div class="text-xs text-slate-400">待复习错题</div>
        <div class="text-2xl font-bold text-rose-500 mt-1">
          {{ loading ? "…" : (wrongStats.active || 0) }}
        </div>
        <div class="text-[11px] text-slate-400 mt-1">共 {{ wrongStats.total || 0 }} 道</div>
      </div>
    </div>

    <!-- 成绩趋势 + 能力分布（五边形） -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm lg:col-span-2">
        <h3 class="font-semibold text-slate-800 mb-3">📈 成绩趋势</h3>
        <TrendLineChart
          v-if="trendChartProps.dates.length"
          v-bind="trendChartProps"
          height="300px"
        />
        <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">
          还没有考试数据，去练习一下吧
        </div>
      </div>
      <div class="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 class="font-semibold text-slate-800 mb-3">🕸️ 能力分布</h3>
        <RadarChart
          v-if="radarProps.indicators.length"
          v-bind="radarProps"
          title="能力分布"
        />
        <div v-else class="h-64 flex items-center justify-center text-slate-400 text-sm">
          录入成绩后查看
        </div>
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
