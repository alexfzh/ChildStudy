<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useChildStore } from "@/stores/child";
import { rewardsAPI, examsAPI } from "@/api";
import AchIcon from "@/components/AchIcon.vue";

const childStore = useChildStore();
const childId = computed(() => childStore.current?.id);

const loading = ref(false);
const achievements = ref([]);
const childAchievements = ref([]);
const exams = ref([]);

const fetchAll = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    const [all, mine, examList] = await Promise.all([
      rewardsAPI.listAchievements(),
      rewardsAPI.childAchievements(childId.value),
      examsAPI.list({ child_id: childId.value }).catch(() => []),
    ]);
    achievements.value = all;
    childAchievements.value = mine;
    exams.value = examList;
  } catch (e) { /* axios 已提示 */ }
  finally { loading.value = false; }
};

onMounted(fetchAll);
watch(() => childStore.currentId, fetchAll);

// 按成就聚合：获得次数、首次/最近获得时间
const earnedStats = computed(() => {
  const map = new Map();
  for (const ca of childAchievements.value) {
    const s = map.get(ca.achievement_id);
    if (s) {
      s.count += 1;
      if (ca.earned_date && ca.earned_date < s.earliest) s.earliest = ca.earned_date;
      if (ca.earned_date && ca.earned_date > s.latest) s.latest = ca.earned_date;
    } else {
      map.set(ca.achievement_id, {
        count: 1,
        earliest: ca.earned_date || "",
        latest: ca.earned_date || "",
      });
    }
  }
  return map;
});
const earnedIds = computed(() => new Set(earnedStats.value.keys()));

// 汇总统计
const unlockedCount = computed(() => earnedIds.value.size);
const totalEarnedCount = computed(() => childAchievements.value.length);

// 点击卡片查看获得历史
const detailAch = ref(null);
const examMap = computed(() => new Map(exams.value.map(e => [e.id, e])));
const detailRecords = computed(() => {
  if (!detailAch.value) return [];
  return childAchievements.value
    .filter(ca => ca.achievement_id === detailAch.value.id)
    .sort((a, b) => (a.earned_date < b.earned_date ? 1 : a.earned_date > b.earned_date ? -1 : b.id - a.id));
});
const examLabel = (examId) => {
  const e = examMap.value.get(examId);
  return e ? `${e.exam_name} · ${e.subject}` : "";
};
const openDetail = (ach) => {
  if (!earnedIds.value.has(ach.id)) return;
  detailAch.value = ach;
};
</script>

<template>
  <div>
    <div class="mb-4">
      <h2 class="text-lg font-semibold text-slate-800">成就墙</h2>
      <p class="text-sm text-slate-500 mt-0.5">
        考试表现自动解锁成就徽章 · 满分/高分/进步等成就可多次获得
        <template v-if="achievements.length">
          · 已解锁 <span class="text-brand-600 font-medium">{{ unlockedCount }}</span>/{{ achievements.length }} 类，
          累计获得 <span class="text-brand-600 font-medium">{{ totalEarnedCount }}</span> 次
        </template>
      </p>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>

    <div v-else-if="achievements.length" class="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
      <div v-for="ach in achievements" :key="ach.id"
        class="card p-3 text-center transition"
        :class="[
          earnedIds.has(ach.id) ? 'border-brand-200 bg-brand-50/30 cursor-pointer hover:shadow-md' : 'opacity-40 grayscale',
        ]"
        @click="openDetail(ach)"
      >
        <div class="text-3xl mb-1"><AchIcon :icon="ach.icon" /></div>
        <div class="text-xs font-semibold text-slate-800 mb-0.5">{{ ach.name }}</div>
        <div class="text-[11px] text-slate-500 mb-1.5 leading-4">{{ ach.description }}</div>
        <template v-if="earnedStats.get(ach.id)">
          <span class="text-[11px] px-1.5 py-0.5 rounded-full bg-brand-100 text-brand-700">
            已获得<template v-if="earnedStats.get(ach.id).count > 1"> ×{{ earnedStats.get(ach.id).count }}</template>
          </span>
          <div class="text-[11px] text-slate-400 mt-1 leading-4">
            <template v-if="earnedStats.get(ach.id).count > 1">
              首次 {{ earnedStats.get(ach.id).earliest }}<br>最近 {{ earnedStats.get(ach.id).latest }}
            </template>
            <template v-else>{{ earnedStats.get(ach.id).earliest }} 获得</template>
          </div>
        </template>
        <span v-else class="text-[11px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-400">未解锁</span>
      </div>
    </div>

    <div v-else class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">🏆</div>
      <div class="text-sm">还没有成就定义</div>
    </div>

    <!-- 获得历史弹窗 -->
    <div v-if="detailAch" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40"
      @click.self="detailAch = null">
      <div class="relative bg-white rounded-xl shadow-xl w-full max-w-sm p-5">
        <button class="absolute top-3 right-3 text-slate-400 hover:text-slate-600 text-lg leading-none"
          @click="detailAch = null">✕</button>
        <div class="flex items-center gap-3 mb-1">
          <div class="text-3xl"><AchIcon :icon="detailAch.icon" /></div>
          <div>
            <div class="text-sm font-semibold text-slate-800">{{ detailAch.name }}</div>
            <div class="text-xs text-slate-500">{{ detailAch.description }}</div>
          </div>
        </div>
        <div class="text-xs text-slate-500 mb-3">
          共获得
          <span class="text-brand-600 font-medium">{{ detailRecords.length }}</span> 次
        </div>
        <div class="max-h-64 overflow-y-auto divide-y divide-slate-100">
          <div v-for="(rec, i) in detailRecords" :key="rec.id" class="flex items-center justify-between py-2">
            <div class="flex items-center gap-2">
              <span class="text-[11px] text-slate-400 w-10">{{ detailRecords.length - i }}</span>
              <span class="text-xs text-slate-700">{{ rec.earned_date }}</span>
            </div>
            <span class="text-[11px] text-slate-400 truncate max-w-[170px] text-right">
              {{ examLabel(rec.exam_id) || "—" }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 额外样式 */
</style>
