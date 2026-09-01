<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { useChildStore } from "@/stores/child";
import BaseChart from "@/components/charts/BaseChart.vue";
import { examsAPI } from "@/api";

const route = useRoute();
const router = useRouter();
const childStore = useChildStore();

const childId = computed(() => childStore.current?.id);

const loading = ref(false);
const exams = ref([]);                    // 该孩子全部考试（侧栏用）
const subject = ref("");                  // 当前科目
const subjects = computed(() => {
  // 从考试 + child.subjects 合并去重
  const set = new Set(childStore.current?.subjects || []);
  exams.value.forEach((e) => set.add(e.subject));
  return Array.from(set);
});

// 单次模式
const singleExamId = ref(null);           // 选中的考试 ID
const singleAnalysis = ref(null);         // 总分分析
const paperAnalysis = ref(null);          // 卷面分析

// 历次模式
const historyAnalysis = ref(null);        // 历次趋势

// Tab 状态
const tab = ref("single");                // 'single' | 'history'

// ============ 数据加载 ============

const fetchExams = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    exams.value = await examsAPI.list({ child_id: childId.value });
    if (!subject.value && exams.value.length) {
      subject.value = exams.value[0].subject;
    }
  } finally {
    loading.value = false;
  }
};

const fetchSingleAnalysis = async () => {
  if (!singleExamId.value) {
    singleAnalysis.value = null;
    paperAnalysis.value = null;
    return;
  }
  loading.value = true;
  try {
    const [a, p] = await Promise.all([
      examsAPI.analyze(singleExamId.value),
      examsAPI.paperAnalysis(singleExamId.value).catch(() => null),
    ]);
    singleAnalysis.value = a;
    paperAnalysis.value = p;
  } catch (e) {
    singleAnalysis.value = null;
    paperAnalysis.value = null;
  } finally {
    loading.value = false;
  }
};

const fetchHistoryAnalysis = async () => {
  if (!subject.value) {
    historyAnalysis.value = null;
    return;
  }
  loading.value = true;
  try {
    historyAnalysis.value = await examsAPI.historyAnalysis({
      child_id: childId.value,
      subject: subject.value,
    });
  } catch {
    historyAnalysis.value = null;
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await fetchExams();
  // URL ?exam_id=X 进入单次分析
  const qid = route.query.exam_id;
  if (qid) {
    singleExamId.value = Number(qid);
    tab.value = "single";
    await fetchSingleAnalysis();
  } else {
    tab.value = "history";
    await fetchHistoryAnalysis();
  }
});

watch(childId, async (id) => {
  if (id) {
    await fetchExams();
    if (tab.value === "single" && singleExamId.value) {
      await fetchSingleAnalysis();
    } else {
      await fetchHistoryAnalysis();
    }
  }
});

watch(subject, async () => {
  if (tab.value === "history") {
    await fetchHistoryAnalysis();
  } else if (singleExamId.value) {
    await fetchSingleAnalysis();
  }
});

watch(singleExamId, async () => {
  if (tab.value === "single") await fetchSingleAnalysis();
});

watch(tab, async (t) => {
  if (t === "single" && singleExamId.value) await fetchSingleAnalysis();
  if (t === "history") await fetchHistoryAnalysis();
});

// ============ 辅助 ============

const currentExam = computed(() =>
  exams.value.find((e) => e.id === singleExamId.value) || null
);

// 同科目考试，按日期倒序
const examsBySubject = computed(() =>
  exams.value
    .filter((e) => e.subject === subject.value)
    .sort((a, b) => (a.exam_date < b.exam_date ? 1 : -1))
);

// 趋势图 option（分数 + 班均）
const trendChartOption = computed(() => {
  if (!historyAnalysis.value || !historyAnalysis.value.score_trend?.length) return null;
  const dates = historyAnalysis.value.score_trend.map((p) => p.date);
  const scoreData = historyAnalysis.value.score_trend.map((p) => [
    p.date,
    p.score,
    p.exam_name,
  ]);
  const avgData = historyAnalysis.value.score_trend
    .filter((p) => p.class_avg_delta !== null)
    .map((p) => [p.date, p.score - p.class_avg_delta]);
  const targetData = historyAnalysis.value.target_progression
    .filter((p) => p.target != null)
    .map((p) => [p.date, p.target]);

  return {
    tooltip: { trigger: "axis" },
    legend: { data: ["分数", "班均（推算）", "目标分"] },
    grid: { left: 40, right: 20, top: 40, bottom: 40 },
    xAxis: { type: "category", data: dates },
    yAxis: { type: "value", min: 0, max: 100 },
    series: [
      {
        name: "分数",
        type: "line",
        smooth: true,
        data: scoreData,
        itemStyle: { color: "#6366f1" },
        areaStyle: { color: "rgba(99,102,241,0.1)" },
      },
      {
        name: "班均（推算）",
        type: "line",
        data: avgData,
        itemStyle: { color: "#94a3b8" },
        lineStyle: { type: "dashed" },
      },
      {
        name: "目标分",
        type: "line",
        data: targetData,
        itemStyle: { color: "#f59e0b" },
        lineStyle: { type: "dotted" },
      },
    ],
  };
});

// 题型聚合图（卷面分析用）
const typeChartOption = computed(() => {
  if (!paperAnalysis.value || !paperAnalysis.value.question_type_stats?.length) return null;
  const types = paperAnalysis.value.question_type_stats;
  const typeLabel = {
    single_choice: "选择题", multi_choice: "多选题", true_false: "判断题",
    fill_blank: "填空题", short_answer: "简答题", calculation: "计算题",
    application: "应用题", essay: "作文", other: "其他",
  };
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { data: ["得分", "失分"] },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: { type: "category", data: types.map((t) => typeLabel[t.question_type] || t.question_type) },
    yAxis: { type: "value" },
    series: [
      {
        name: "得分",
        type: "bar",
        stack: "score",
        data: types.map((t) => t.scored),
        itemStyle: { color: "#10b981" },
      },
      {
        name: "失分",
        type: "bar",
        stack: "score",
        data: types.map((t) => t.loss_score),
        itemStyle: { color: "#ef4444" },
      },
    ],
  };
});

const trendLabel = (t) => {
  const map = {
    rising: { text: "上升", cls: "text-emerald-600" },
    falling: { text: "下降", cls: "text-rose-600" },
    stable: { text: "平稳", cls: "text-slate-600" },
  };
  return map[t] || { text: t, cls: "" };
};

const trendStrengthLabel = (s) => {
  const map = {
    significant: "显著",
    moderate: "中等",
    weak: "微弱",
    flat: "无变化",
  };
  return map[s] || s;
};

const stabilityLabel = (s) => {
  const map = { stable: "稳定", fluctuating: "波动", volatile: "剧烈" };
  return map[s] || s;
};

const positionLabel = (p) => {
  const map = {
    best: "历史最佳",
    near_best: "上游",
    middle: "中等",
    near_worst: "下游",
    worst: "历史最低",
    only: "唯一一次",
  };
  return map[p] || p;
};
</script>

<template>
  <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
    <div>
      <h2 class="text-lg font-semibold text-slate-800">考试分析</h2>
      <p class="text-sm text-slate-500 mt-0.5">单科单次卷面分析 + 历次趋势对比</p>
    </div>
    <button class="btn-ghost" @click="router.push({ name: 'exams' })">← 返回考试管理</button>
  </div>

  <div v-if="!childId" class="card p-10 text-center text-slate-400">
    <div class="text-4xl mb-2">👶</div>
    <div class="text-sm">请先在「孩子档案」中选择孩子</div>
  </div>

  <template v-else>
    <!-- 顶部 Tab + 控件 -->
    <div class="card p-3 mb-4 flex flex-wrap gap-3 items-center">
      <div class="flex gap-1">
        <button
          class="px-3 py-1 text-sm rounded transition"
          :class="tab === 'history' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'"
          @click="tab = 'history'"
        >📈 历次趋势</button>
        <button
          class="px-3 py-1 text-sm rounded transition"
          :class="tab === 'single' ? 'bg-brand-600 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'"
          @click="tab = 'single'"
        >📊 单次分析</button>
      </div>
      <el-select
        v-if="tab === 'history'"
        v-model="subject"
        filterable
        size="default"
        class="!w-40"
        placeholder="选择科目"
      >
        <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select
        v-else
        v-model="singleExamId"
        filterable
        size="default"
        class="!w-72"
        placeholder="选择某次考试"
      >
        <el-option
          v-for="e in examsBySubject"
          :key="e.id"
          :label="`${e.subject} · ${e.exam_name} · ${e.exam_date} · ${e.score}分`"
          :value="e.id"
        />
      </el-select>
    </div>

    <!-- 历次趋势 Tab -->
    <div v-if="tab === 'history'">
      <div v-if="!historyAnalysis || historyAnalysis.exam_count === 0" class="card p-10 text-center text-slate-400">
        <div class="text-4xl mb-2">📊</div>
        <div class="text-sm">{{ subject }} 暂无考试记录</div>
      </div>
      <template v-else>
        <!-- 概览卡 -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div class="card p-4">
            <div class="text-xs text-slate-500">考试次数</div>
            <div class="text-2xl font-bold text-slate-800 mt-1">{{ historyAnalysis.exam_count }}</div>
          </div>
          <div class="card p-4">
            <div class="text-xs text-slate-500">趋势</div>
            <div class="text-2xl font-bold mt-1" :class="trendLabel(historyAnalysis.trend_direction).cls">
              {{ trendLabel(historyAnalysis.trend_direction).text }}
              <span class="text-sm font-normal text-slate-500 ml-1">
                ({{ trendStrengthLabel(historyAnalysis.trend_strength) }})
              </span>
            </div>
          </div>
          <div class="card p-4">
            <div class="text-xs text-slate-500">稳定性</div>
            <div class="text-2xl font-bold text-slate-800 mt-1">
              {{ stabilityLabel(historyAnalysis.volatility.stability) }}
            </div>
            <div class="text-xs text-slate-400 mt-0.5">σ = {{ historyAnalysis.volatility.std_dev }}</div>
          </div>
          <div class="card p-4">
            <div class="text-xs text-slate-500">期间</div>
            <div class="text-sm font-medium text-slate-800 mt-1">
              {{ historyAnalysis.period.start_date }} ~ {{ historyAnalysis.period.end_date }}
            </div>
          </div>
        </div>

        <!-- 趋势图 -->
        <div class="card p-4 mb-4" v-if="trendChartOption">
          <div class="text-sm font-medium text-slate-700 mb-2">📈 分数走势</div>
          <BaseChart :option="trendChartOption" height="320px" />
        </div>

        <!-- 洞察 -->
        <div v-if="historyAnalysis.insights?.length" class="card p-4 mb-4">
          <div class="text-sm font-medium text-slate-700 mb-2">💡 智能洞察</div>
          <ul class="space-y-1.5 text-sm text-slate-700">
            <li v-for="(i, idx) in historyAnalysis.insights" :key="idx" class="flex gap-2">
              <span class="text-brand-500">•</span>
              <span>{{ i }}</span>
            </li>
          </ul>
        </div>

        <!-- 知识点演化 -->
        <div v-if="historyAnalysis.knowledge_point_evolution?.length" class="card p-4">
          <div class="text-sm font-medium text-slate-700 mb-3">📚 知识点演化</div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-slate-500 border-b">
                      <th class="py-2">知识点</th>
                      <th class="py-2">出现次数</th>
                      <th class="py-2">累计失分</th>
                    </tr>
              </thead>
              <tbody>
                <tr
                  v-for="kp in historyAnalysis.knowledge_point_evolution"
                  :key="kp.knowledge_point"
                  class="border-b last:border-b-0"
                >
                  <td class="py-2">{{ kp.knowledge_point }}</td>
                  <td class="py-2">{{ kp.appearances }}</td>
                  <td class="py-2 text-rose-600">{{ kp.lost_score_total }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- 单次分析 Tab -->
    <div v-else>
      <div v-if="!singleExamId" class="card p-10 text-center text-slate-400">
        <div class="text-4xl mb-2">🎯</div>
        <div class="text-sm">请选择某次考试进行分析</div>
      </div>
      <template v-else-if="!singleAnalysis" class="text-slate-400">加载中…</template>
      <template v-else>
        <!-- 总分概览卡 -->
        <div v-if="currentExam" class="card p-4 mb-4">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div>
              <div class="text-xs text-slate-500">{{ currentExam.subject }} · {{ currentExam.exam_name }}</div>
              <div class="text-2xl font-bold mt-1">
                {{ singleAnalysis.score }} / {{ singleAnalysis.full_score }}
                <span class="text-base text-slate-500 ml-1">({{ singleAnalysis.percentage }}%)</span>
              </div>
            </div>
            <div class="text-right text-sm text-slate-500">
              <div>📅 {{ singleAnalysis.exam_date }}</div>
              <div v-if="singleAnalysis.trend_position">📊 {{ positionLabel(singleAnalysis.trend_position.position) }} · {{ singleAnalysis.trend_position.rank_in_n }}/{{ singleAnalysis.trend_position.total_n }} · {{ singleAnalysis.trend_position.percentile }}%</div>
            </div>
          </div>
        </div>

        <!-- 总分维度洞察 -->
        <div v-if="singleAnalysis.insights?.length" class="card p-4 mb-4">
          <div class="text-sm font-medium text-slate-700 mb-2">💡 总分洞察</div>
          <ul class="space-y-1.5 text-sm text-slate-700">
            <li v-for="(i, idx) in singleAnalysis.insights" :key="idx" class="flex gap-2">
              <span class="text-brand-500">•</span>
              <span>{{ i }}</span>
            </li>
          </ul>
        </div>

        <!-- 卷面分析 -->
        <div v-if="paperAnalysis && paperAnalysis.section_stats?.length">
          <div class="text-base font-semibold text-slate-800 mt-4 mb-2">📋 卷面分析</div>
          <!-- 题型得分/失分图 -->
          <div v-if="typeChartOption" class="card p-4 mb-4">
            <div class="text-sm font-medium text-slate-700 mb-2">题型得分/失分</div>
            <BaseChart :option="typeChartOption" height="280px" />
          </div>

          <!-- 卷面洞察 -->
          <div v-if="paperAnalysis.insights?.length" class="card p-4 mb-4">
            <div class="text-sm font-medium text-slate-700 mb-2">💡 卷面洞察</div>
            <ul class="space-y-1.5 text-sm text-slate-700">
              <li v-for="(i, idx) in paperAnalysis.insights" :key="idx" class="flex gap-2">
                <span class="text-brand-500">•</span>
                <span>{{ i }}</span>
              </li>
            </ul>
          </div>

          <!-- 知识点丢分 TOP -->
          <div v-if="paperAnalysis.knowledge_point_loss?.length" class="card p-4 mb-4">
            <div class="text-sm font-medium text-slate-700 mb-3">📚 知识点丢分 TOP</div>
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="text-left text-slate-500 border-b">
                    <th class="py-2">知识点</th>
                    <th class="py-2">丢分</th>
                    <th class="py-2">涉及题数</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="kp in paperAnalysis.knowledge_point_loss"
                    :key="kp.knowledge_point"
                    class="border-b last:border-b-0"
                  >
                    <td class="py-2">{{ kp.knowledge_point }}</td>
                    <td class="py-2 text-rose-600 font-medium">{{ kp.lost_score }}</td>
                    <td class="py-2">{{ kp.question_count }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- 最难 TOP5 -->
          <div v-if="paperAnalysis.hardest_questions?.length" class="card p-4">
            <div class="text-sm font-medium text-slate-700 mb-3">🔥 最难 TOP5（丢分最多）</div>
            <div class="space-y-1.5 text-sm">
              <div
                v-for="q in paperAnalysis.hardest_questions"
                :key="q.question_id"
                class="flex items-center justify-between border-b last:border-b-0 pb-1.5"
              >
                <div class="flex-1">
                  <span class="text-slate-500">第 {{ q.number }} 题</span>
                  <span class="ml-2 text-slate-700">{{ q.section_name }}</span>
                </div>
                <div class="text-rose-600">
                  {{ q.scored }} / {{ q.max_score }}（失 {{ q.loss }}）
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="card p-8 text-center text-slate-400">
          <div class="text-4xl mb-2">📋</div>
          <div class="text-sm">本次考试未录入卷面题目（仅总分分析可用）</div>
        </div>
      </template>
    </div>
  </template>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>