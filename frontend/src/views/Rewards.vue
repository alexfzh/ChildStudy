<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { rewardsAPI } from "@/api";

const childStore = useChildStore();
const childId = computed(() => childStore.current?.id);

const loading = ref(false);
const ranks = ref([]);
const pointsSummary = ref(null);
const shopItems = ref([]);
const history = ref([]);
const childAchievements = ref([]);

const fetchAll = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    const [r, p, s, h] = await Promise.all([
      rewardsAPI.ranks(childId.value),
      rewardsAPI.points(childId.value),
      rewardsAPI.shop(childId.value),
      rewardsAPI.rewardHistory(childId.value),
    ]);
    ranks.value = r;
    pointsSummary.value = p;
    shopItems.value = s;
    history.value = h;
    const ach = await rewardsAPI.childAchievements(childId.value);
    childAchievements.value = ach;
  } catch (e) { /* axios 已提示 */ }
  finally { loading.value = false; }
};

onMounted(fetchAll);
// 监听 currentId 变化（切换孩子时重新拉数据），加 immediate 覆盖 onMounted 调用时 childId 还未加载的竟态
watch(() => childStore.current?.id, fetchAll, { immediate: true });

const redeem = async (item) => {
  try {
    await ElMessageBox.confirm(`兑换「${item.reward.name}」需要 ${item.reward.cost_points} 积分，确认吗？`, "兑换奖励", { type: "warning" });
    await rewardsAPI.redeem(childId.value, item.reward.id);
    ElMessage.success("兑换成功！");
    await fetchAll();
  } catch (e) { /* 取消 */ }
};

// ============ 积分流水 ============
// 积分来源 → 图标/标签的映射（与后端 PointsLog.source 枚举对齐）
const SOURCE_META = {
  exam_reward: { icon: "📝", label: "考试奖励", tone: "emerald" },
  redemption:  { icon: "🛒", label: "商城兑换", tone: "rose" },
  bonus:       { icon: "🎁", label: "额外奖励", tone: "amber" },
  manual:      { icon: "✍️", label: "手动调整", tone: "slate" },
};
const sourceMeta = (src) => SOURCE_META[src] || { icon: "·", label: src || "其他", tone: "slate" };

// 原始流水 + 折叠/过滤状态
const allLogs = computed(() => pointsSummary.value?.recent_logs || []);
const showAllLogs = ref(false);     // 折叠状态
const logFilter = ref("all");        // 来源过滤: 'all' | 'exam_reward' | 'redemption' | ...

// 按过滤后展示的日志（最新在前）
const filteredLogs = computed(() => {
  const arr = allLogs.value;
  if (logFilter.value === "all") return arr;
  return arr.filter((l) => l.source === logFilter.value);
});
const displayedLogs = computed(() =>
  showAllLogs.value ? filteredLogs.value : filteredLogs.value.slice(0, 5)
);
// 各 source 计数（用于过滤 chip）
const logSourceCounts = computed(() => {
  const counts = { all: allLogs.value.length };
  for (const l of allLogs.value) {
    counts[l.source] = (counts[l.source] || 0) + 1;
  }
  return counts;
});

// 积分流水时间格式器（只取月-日 时:分，避免 ISO 字符串太长）
const fmtDateTime = (s) => {
  if (!s) return "";
  return s.replace("T", " ").slice(5, 16);
};

const tierColor = (tier) => {
  const map = { "青铜": "#8B7355", "白银": "#C0C0C0", "黄金": "#FFD700", "铂金": "#00BFFF", "钻石": "#B9F2FF", "星耀": "#FF6B9D", "王者": "#FF4500" };
  return map[tier] || "#6366f1";
};

const totalPoints = computed(() => pointsSummary.value?.total ?? 0);

// 称号墙：已获得的成就，按类型分组
const TIER_BG = {
  "🎯": "bg-slate-100 text-slate-700",
  "📈": "bg-blue-50 text-blue-700",
  "🥇": "bg-amber-50 text-amber-700",
  "🧠": "bg-purple-50 text-purple-700",
  "💎": "bg-violet-50 text-violet-700",
  "🔥": "bg-red-50 text-red-700",
  "📚": "bg-green-50 text-green-700",
  "💪": "bg-orange-50 text-orange-700",
  "🧩": "bg-teal-50 text-teal-700",
  "👑": "bg-yellow-50 text-yellow-700",
  "🌟": "bg-brand-50 text-brand-700",
  "🌈": "bg-pink-50 text-pink-700",
  "svg:gold-bucket": "bg-amber-50 text-amber-700",
};
const earnedTitles = computed(() => {
  if (!childAchievements.value) return [];
  return childAchievements.value
    .filter(a => a.achievement)
    .map(a => ({
      id: a.id,
      name: a.achievement.name,
      icon: a.achievement.icon,
      bgColor: TIER_BG[a.achievement.icon] || "bg-slate-100 text-slate-700",
      textColor: "#1e293b",
    }));
});
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">奖励商城</h2>
        <p class="text-sm text-slate-500 mt-0.5">用考试积分兑换奖励</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="card px-4 py-2 flex items-center gap-2">
          <span class="text-xl">💰</span>
          <span class="text-lg font-semibold text-slate-800">{{ totalPoints }}</span>
          <span class="text-xs text-slate-500">积分</span>
        </div>
      </div>
    </div>

    <!-- 我的称号墙 -->
    <div v-if="earnedTitles.length" class="card p-5 mb-5">
      <h3 class="font-semibold text-slate-800 mb-3">🎖️ 我的称号</h3>
      <div class="flex flex-wrap gap-2">
        <span v-for="title in earnedTitles" :key="title.id"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium"
          :style="{ backgroundColor: title.bgColor, color: title.textColor }"
        >
          <span>{{ title.name }}</span>
        </span>
      </div>
    </div>

    <!-- 段位 -->
    <div v-if="ranks.length" class="card p-5 mb-5">
      <h3 class="font-semibold text-slate-800 mb-3">🏆 当前段位</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div v-for="r in ranks" :key="r.subject" class="p-4 rounded-xl border-2 text-center" :style="{ borderColor: tierColor(r.tier), backgroundColor: tierColor(r.tier) + '10' }">
          <div class="text-2xl mb-1">{{ r.tier }}</div>
          <div class="text-xs text-slate-500 mb-1">{{ r.subject }}</div>
          <div class="text-xs" :style="{ color: tierColor(r.tier) }">{{ r.avg_score }}分 · ⭐{{ r.stars }} · {{ r.exam_count }}次</div>
        </div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>

    <!-- 奖励商城 -->
    <div v-if="shopItems.length" class="card p-5 mb-5">
      <h3 class="font-semibold text-slate-800 mb-3">🎁 奖励商城</h3>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div v-for="item in shopItems" :key="item.reward.id"
          class="p-4 rounded-xl border text-center transition"
          :class="item.can_afford ? 'border-slate-200 hover:border-brand-300 hover:shadow-sm cursor-pointer' : 'border-slate-100 opacity-50'"
          @click="item.can_afford && redeem(item)"
        >
          <div class="text-3xl mb-2">{{ item.reward.icon }}</div>
          <div class="text-sm font-medium text-slate-700 mb-1">{{ item.reward.name }}</div>
          <div class="text-xs text-slate-400 mb-2">{{ item.reward.description || '' }}</div>
          <div class="text-sm font-semibold" :class="item.can_afford ? 'text-brand-600' : 'text-rose-500'">
            {{ item.reward.cost_points > 0 ? item.reward.cost_points + ' 积分' : '免费' }}
          </div>
          <button v-if="item.can_afford" class="btn-primary text-xs mt-2 w-full">兑换</button>
          <button v-else class="btn-ghost text-xs mt-2 w-full opacity-50" disabled>积分不足</button>
        </div>
      </div>
    </div>

    <!-- 积分流水（获取 + 消费记录） -->
    <div v-if="allLogs.length" class="card p-5 mb-5">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h3 class="font-semibold text-slate-800">💰 积分流水</h3>
        <div class="flex items-center gap-1.5 flex-wrap">
          <!-- 来源过滤 chip -->
          <button
            v-for="src in ['all','exam_reward','redemption','bonus','manual']"
            :key="src"
            type="button"
            :disabled="!logSourceCounts[src]"
            class="px-2.5 py-0.5 rounded-full text-xs border transition select-none disabled:opacity-40 disabled:cursor-not-allowed"
            :class="logFilter === src ? 'bg-brand-500 text-white border-brand-500' : 'bg-white text-slate-500 border-slate-200 hover:border-brand-300'"
            @click="logFilter = src"
          >
            {{ src === 'all' ? '全部' : sourceMeta(src).label }}
            <span class="ml-1 text-[10px] opacity-75">({{ logSourceCounts[src] || 0 }})</span>
          </button>
        </div>
      </div>

      <!-- 流水列表 -->
      <div class="space-y-2">
        <div v-for="log in displayedLogs" :key="log.id"
          class="flex items-center justify-between p-3 rounded-lg border"
          :class="log.points > 0 ? 'bg-emerald-50/40 border-emerald-100' : 'bg-rose-50/40 border-rose-100'"
        >
          <div class="flex items-center gap-3 min-w-0">
            <span class="text-xl">{{ sourceMeta(log.source).icon }}</span>
            <div class="min-w-0">
              <div class="text-sm font-medium text-slate-700 truncate">{{ log.description }}</div>
              <div class="text-xs text-slate-400 mt-0.5">
                <span class="inline-block px-1.5 py-0.5 rounded mr-1.5"
                  :class="{
                    'bg-emerald-100 text-emerald-700': log.source === 'exam_reward',
                    'bg-rose-100 text-rose-700': log.source === 'redemption',
                    'bg-amber-100 text-amber-700': log.source === 'bonus',
                    'bg-slate-100 text-slate-600': log.source === 'manual',
                  }"
                >{{ sourceMeta(log.source).label }}</span>
                {{ fmtDateTime(log.created_at) }}
              </div>
            </div>
          </div>
          <div class="text-base font-semibold flex-shrink-0"
            :class="log.points > 0 ? 'text-emerald-600' : 'text-rose-500'">
            {{ log.points > 0 ? '+' : '' }}{{ log.points }}
          </div>
        </div>
      </div>

      <!-- 折叠/展开控制 -->
      <div v-if="filteredLogs.length > 5" class="text-center mt-3">
        <button class="btn-ghost text-xs" @click="showAllLogs = !showAllLogs">
          {{ showAllLogs ? '收起 ▴' : `查看全部 ${filteredLogs.length} 条 ▾` }}
        </button>
      </div>
      <div v-else-if="logFilter !== 'all'" class="text-center mt-3">
        <button class="btn-ghost text-xs" @click="logFilter = 'all'">清除筛选</button>
      </div>
    </div>

    <!-- 兑换记录 -->
    <div v-if="history.length" class="card p-5">
      <h3 class="font-semibold text-slate-800 mb-3">📋 兑换记录</h3>
      <div class="space-y-2">
        <div v-for="h in history" :key="h.id" class="flex items-center justify-between p-3 rounded-lg bg-slate-50">
          <div class="flex items-center gap-3">
            <span class="text-xl">{{ h.reward?.icon || '🎁' }}</span>
            <div>
              <div class="text-sm font-medium text-slate-700">{{ h.reward?.name || '未知奖励' }}</div>
              <div class="text-xs text-slate-400">{{ h.earned_date }}</div>
            </div>
          </div>
          <div class="text-sm font-semibold text-rose-500">-{{ h.points_spent }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 额外样式 */
</style>
