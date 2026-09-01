<template>
  <div class="space-y-6">
    <!-- 头部 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">📚 教材学习进度</h1>
        <p class="text-sm text-slate-500 mt-1">
          按教材单元追踪掌握度 · 答题自动更新 · 完成解锁小成就 🎉
        </p>
      </div>
      <div class="flex items-center gap-2">
        <el-select v-model="selectedVersionId" placeholder="选择教材版本" class="!w-72" @change="reload">
          <el-option
            v-for="v in versions"
            :key="v.id"
            :label="`${v.name}${v.term === 'A' ? '（上）' : v.term === 'B' ? '（下）' : ''}`"
            :value="v.id"
          />
        </el-select>
      </div>
    </div>

    <!-- 概览卡片 -->
    <div v-if="summary" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <el-card shadow="never" class="!border-slate-200">
        <div class="text-xs text-slate-500 mb-1">总体掌握度</div>
        <div class="text-3xl font-bold text-brand-600">{{ summary.mastery_pct }}%</div>
        <div class="text-xs text-slate-400 mt-1">{{ masterCount }} / {{ summary.units.length }} Unit 已掌握</div>
      </el-card>
      <el-card shadow="never" class="!border-slate-200">
        <div class="text-xs text-slate-500 mb-1">连胜单元</div>
        <div class="text-3xl font-bold text-orange-500">{{ summary.streak_units }} 🔥</div>
        <div class="text-xs text-slate-400 mt-1">连续 mastered 单元数</div>
      </el-card>
      <el-card shadow="never" class="!border-slate-200">
        <div class="text-xs text-slate-500 mb-1">累计积分</div>
        <div class="text-3xl font-bold text-green-600">+{{ summary.total_points }}</div>
        <div class="text-xs text-slate-400 mt-1">教材学习奖励</div>
      </el-card>
      <el-card shadow="never" class="!border-slate-200">
        <div class="text-xs text-slate-500 mb-1">解锁成就</div>
        <div class="text-3xl font-bold text-purple-600">{{ summary.total_achievements }} 🏆</div>
        <div class="text-xs text-slate-400 mt-1">来自单元掌握 / 连胜</div>
      </el-card>
    </div>

    <!-- 学习建议 -->
    <el-card v-if="summary && nextUnit" shadow="never" class="!border-amber-300 !bg-amber-50">
      <div class="flex items-start gap-3">
        <div class="text-3xl">✨</div>
        <div class="flex-1">
          <div class="text-sm font-semibold text-amber-900">下一步推荐</div>
          <div class="text-sm text-amber-800 mt-1">
            下一个未掌握的单元是 <b>{{ nextUnit.code }}</b>
            <span class="ml-1">{{ nextUnit.title_en }}（{{ nextUnit.title_zh }}）</span>
            <span v-if="nextUnit.sound" class="ml-2 text-amber-700">🔤 拼读：{{ nextUnit.sound }}</span>
          </div>
          <div class="mt-2 flex gap-2">
            <el-button type="primary" size="small" @click="goPractice(nextUnit)">📝 练这个 Unit</el-button>
            <el-button v-if="nextUnit.big_task" size="small" @click="goProject(nextUnit)">🎨 完成 Big Task</el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Unit 列表 -->
    <div v-if="summary" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <el-card
        v-for="u in summary.units"
        :key="u.id"
        shadow="hover"
        class="!border-slate-200 transition-all"
        :class="statusClass(u)"
      >
        <div class="flex items-start justify-between mb-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-bold text-slate-800">{{ u.code }}</span>
              <span class="text-base font-semibold text-slate-700 truncate">{{ u.title_en }}</span>
            </div>
            <div class="text-xs text-slate-500 mt-0.5">{{ u.title_zh }} · p.{{ u.page_start }}-{{ u.page_end }}</div>
          </div>
          <el-tag v-if="statusOf(u) === 'mastered'" type="success" size="small">已掌握</el-tag>
          <el-tag v-else-if="statusOf(u) === 'in_progress'" type="warning" size="small">进行中</el-tag>
          <el-tag v-else type="info" size="small">未开始</el-tag>
        </div>

        <!-- 主题词预览 -->
        <div v-if="u.topic_words.length" class="flex flex-wrap gap-1 mb-3">
          <span
            v-for="w in u.topic_words.slice(0, 6)"
            :key="w"
            class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-700"
          >{{ w }}</span>
          <span v-if="u.topic_words.length > 6" class="text-xs text-slate-400">+{{ u.topic_words.length - 6 }}</span>
        </div>

        <!-- Sound 拼读 -->
        <div v-if="u.sound" class="text-xs mb-3 flex items-center gap-2">
          <span class="px-1.5 py-0.5 rounded bg-pink-100 text-pink-700">🔤 {{ u.sound }}</span>
          <span class="text-slate-500">{{ (u.sound_examples || []).slice(0, 3).join(' / ') }}</span>
        </div>

        <!-- 知识点标签 -->
        <div v-if="(kpsByUnitId[u.id] || []).length" class="text-xs mb-3 flex flex-wrap gap-1">
          <span
            v-for="kp in (kpsByUnitId[u.id] || []).slice(0, 4)"
            :key="kp.knowledge_point_id"
            class="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700"
            :title="kp.name"
          >🏷️ {{ kp.name }}</span>
          <span v-if="(kpsByUnitId[u.id] || []).length > 4" class="text-slate-400">+{{ (kpsByUnitId[u.id] || []).length - 4 }}</span>
        </div>

        <!-- 结构 -->
        <div v-if="u.structure" class="text-xs text-slate-600 mb-3">
          <span class="text-slate-400">📐</span> {{ u.structure }}
        </div>

        <!-- 进度条 -->
        <div class="space-y-2">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-500">完成度</span>
            <span class="text-slate-700 font-medium">{{ progressOf(u).completion_pct }}%</span>
          </div>
          <el-progress
            :percentage="progressOf(u).completion_pct"
            :stroke-width="6"
            :show-text="false"
            :color="progressColor(u)"
          />
          <div class="flex items-center justify-between text-xs text-slate-500">
            <span>📝 {{ progressOf(u).total_attempts }} 题</span>
            <span>✅ 准确率 {{ progressOf(u).accuracy }}%</span>
          </div>
        </div>

        <!-- 知识点掌握度（可展开） -->
        <div v-if="(kpsByUnitId[u.id] || []).length" class="mb-3">
          <div class="flex items-center justify-between cursor-pointer" @click="toggleKpDetail(u)">
            <div class="text-xs font-medium text-slate-600">🎯 知识点掌握度 ({{ (kpDetailOf(u)?.kp_details || []).length }} KP)</div>
            <span class="text-xs text-brand-600">{{ expandedKpUnitId === u.id ? '收起' : '展开' }}</span>
          </div>
          <div v-if="expandedKpUnitId === u.id && kpDetailOf(u)" class="mt-2 space-y-1.5">
            <div
              v-for="kp in kpDetailOf(u).kp_details"
              :key="kp.knowledge_point_id"
              class="flex items-center justify-between text-xs py-1 px-2 rounded bg-slate-50"
            >
              <span class="text-slate-700 truncate flex-1">{{ kpName(kp.knowledge_point_id, u.id) }}</span>
              <div class="flex items-center gap-2 ml-2">
                <span class="text-slate-500">{{ kp.accuracy }}%</span>
                <span
                  class="px-1.5 py-0.5 rounded text-white text-[10px] font-medium"
                  :style="{ backgroundColor: masteryColor(kp.mastery_level) }"
                >
                  {{ masteryLabel(kp.mastery_level) }}
                </span>
              </div>
            </div>
            <div v-if="!(kpDetailOf(u)?.kp_details || []).length" class="text-xs text-slate-400 py-1">
              该 Unit 暂无 KP 掌握度数据（先做几道题积累吧）
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="mt-4 flex gap-2">
          <el-button size="small" plain @click="goPractice(u)">📝 练一练</el-button>
          <el-button v-if="u.is_project" size="small" plain type="primary" @click="goProject(u)">🎨 作品</el-button>
          <el-button size="small" plain @click="toggleWords(u)">
            {{ expandedUnitId === u.id ? '收起' : '查看主题词' }}
          </el-button>
        </div>

        <!-- 主题词展开 -->
        <div v-if="expandedUnitId === u.id && u.topic_words.length" class="mt-3 pt-3 border-t border-slate-100">
          <div class="text-xs font-medium text-slate-600 mb-1.5">全部主题词</div>
          <div class="flex flex-wrap gap-1">
            <span v-for="w in u.topic_words" :key="w" class="text-xs px-2 py-0.5 rounded bg-brand-50 text-brand-700">
              {{ w }}
            </span>
          </div>
          <div v-if="u.big_task" class="mt-3 text-xs">
            <div class="font-medium text-slate-600 mb-1">🎯 Big Task</div>
            <div class="text-slate-700">{{ u.big_task }}</div>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-if="!summary && !loading" description="请选择教材版本" />
    <el-empty v-if="!loading && versions.length === 0" description="暂无教材版本" />
    <div v-if="loading" v-loading="true" class="!min-h-[200px]"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useChildStore } from "@/stores/child";
import { textbookAPI, studyProgressAPI, questionBanksAPI, kpProgressAPI } from "@/api";

const kpsByUnitId = ref({});
// 新增：KP 掌握度数据（per unit）
const kpMasteryByUnitId = ref({});
const expandedKpUnitId = ref(null);

const MASTERY_LABELS = { new: "新学", learning: "学习中", strong: "较扎实", mastered: "已掌握" };
const MASTERY_COLORS = { new: "#94a3b8", learning: "#f59e0b", strong: "#3b82f6", mastered: "#10b981" };

async function loadKpsForUnits(units) {
  const result = {};
  await Promise.all(
    units.map(async (u) => {
      try {
        result[u.id] = await textbookAPI.listKnowledgePointsForUnit(u.id);
      } catch {
        result[u.id] = [];
      }
    })
  );
  kpsByUnitId.value = result;
}

async function loadKpMasteryForUnits(units) {
  const childId = childStore.current?.id;
  if (!childId) return;
  const result = {};
  await Promise.all(
    units.map(async (u) => {
      try {
        result[u.id] = await kpProgressAPI.getForUnit(childId, u.id);
      } catch {
        result[u.id] = null;
      }
    })
  );
  kpMasteryByUnitId.value = result;
}

const router = useRouter();
const childStore = useChildStore();

const loading = ref(false);
const versions = ref([]);
const selectedVersionId = ref(null);
const summary = ref(null);
const expandedUnitId = ref(null);

const masterCount = computed(() => {
  if (!summary.value) return 0;
  return Object.values(summary.value.progress_map || {}).filter(
    (p) => p.status === "mastered"
  ).length;
});

const nextUnit = computed(() => {
  if (!summary.value) return null;
  const units = summary.value.units;
  const map = summary.value.progress_map || {};
  for (const u of units) {
    const p = map[u.id];
    if (!p || p.status !== "mastered") return u;
  }
  return null;
});

function statusOf(u) {
  if (!summary.value) return "not_started";
  const p = summary.value.progress_map?.[u.id];
  return p?.status || "not_started";
}

function progressOf(u) {
  if (!summary.value) return { completion_pct: 0, total_attempts: 0, accuracy: 0 };
  const p = summary.value.progress_map?.[u.id] || {};
  return {
    completion_pct: p.completion_pct || 0,
    total_attempts: p.total_attempts || 0,
    accuracy: p.accuracy || 0,
  };
}

function statusClass(u) {
  const s = statusOf(u);
  if (s === "mastered") return "!border-green-300";
  if (s === "in_progress") return "!border-amber-300";
  return "";
}

function progressColor(u) {
  const s = statusOf(u);
  if (s === "mastered") return "#10b981";
  if (s === "in_progress") return "#f59e0b";
  return "#94a3b8";
}

function toggleWords(u) {
  expandedUnitId.value = expandedUnitId.value === u.id ? null : u.id;
}

function toggleKpDetail(u) {
  expandedKpUnitId.value = expandedKpUnitId.value === u.id ? null : u.id;
  if (expandedKpUnitId.value === u.id && !kpMasteryByUnitId.value[u.id]) {
    loadKpMasteryForUnits([u]);
  }
}

function masteryColor(level) {
  return MASTERY_COLORS[level] || MASTERY_COLORS.new;
}

function masteryLabel(level) {
  return MASTERY_LABELS[level] || level;
}

function kpDetailOf(u) {
  return kpMasteryByUnitId.value[u.id] || null;
}

function kpName(kpId, unitId) {
  const kps = kpsByUnitId.value[unitId] || [];
  const kp = kps.find((k) => k.knowledge_point_id === kpId);
  return kp?.name || `KP-${kpId}`;
}

async function loadVersions() {
  try {
    versions.value = await textbookAPI.listVersions({ is_active: true });
    if (versions.value.length && !selectedVersionId.value) {
      const english = versions.value.filter((v) => v.subject === "英语");
      selectedVersionId.value = (english[0] || versions.value[0])?.id;
    }
  } catch (e) {
    ElMessage.error("教材版本加载失败");
  }
}

async function reload() {
  const childId = childStore.current?.id;
  if (!childId) {
    ElMessage.warning("请先选择孩子");
    return;
  }
  if (!selectedVersionId.value) return;
  loading.value = true;
  try {
    summary.value = await studyProgressAPI.getSummary(childId, selectedVersionId.value);
    await loadKpsForUnits(summary.value.units);
  } catch (e) {
    ElMessage.error("进度加载失败");
  } finally {
    loading.value = false;
  }
}

async function goPractice(u) {
  const childId = childStore.current?.id;
  if (!childId) {
    ElMessage.warning("请先选择孩子");
    return;
  }
  const banks = await questionBanksAPI.list({ grade: "四年级", subject: "英语" });
  const bank = banks[0];
  if (!bank) {
    ElMessage.warning("暂未找到题库");
    return;
  }
  router.push({
    name: "exercise",
    query: { bank_id: bank.id, child_id: childId, knowledge_point: `${u.code}` },
  });
}

function goProject(u) {
  router.push({ name: "project-works", query: { unit_id: u.id } });
}

onMounted(async () => {
  await loadVersions();
  setTimeout(() => reload(), 200);
});
</script>

<style scoped>
.card-grid {
  display: grid;
  gap: 1rem;
}
</style>
