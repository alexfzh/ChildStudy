<template>
  <div class="max-w-3xl mx-auto">
    <!-- 阶段1：组卷设置 -->
    <div v-if="phase === 'setup'" class="space-y-6">
      <div class="text-center mb-6">
        <h1 class="text-2xl font-bold text-slate-800">✏️ 开始练习</h1>
        <p class="text-sm text-slate-500 mt-1">选择题目数量和知识点，开始巩固练习</p>
      </div>

      <el-card shadow="never" class="!border-slate-200">
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">练习模式</label>
            <el-radio-group v-model="form.mode" class="w-full">
              <el-radio value="manual">✋ 手动选题</el-radio>
              <el-radio value="recommend">💡 错题推荐</el-radio>
            </el-radio-group>
            <div v-if="form.mode === 'recommend'" class="mt-2 text-xs text-amber-600 bg-amber-50 p-2 rounded">
              💡 系统将根据错题本的薄弱知识点自动匹配题目（新 KP 体系：主 KP 优先 + 同单元拓展 + 兜底）
            </div>
          </div>

          <div v-if="form.mode === 'manual'">
            <label class="block text-sm font-medium text-slate-700 mb-1">知识点（留空=随机）</label>
            <el-select
              ref="kpSelectRef"
              v-model="form.knowledge_points"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入知识点"
              class="!w-full"
              @change="onKpChange"
            >
              <el-option
                v-for="kp in allKnowledgePoints"
                :key="kp"
                :label="kp"
                :value="kp"
              />
            </el-select>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">难度</label>
            <el-radio-group v-model="form.difficulty">
              <el-radio value="">全部</el-radio>
              <el-radio value="easy">简单</el-radio>
              <el-radio value="normal">中等</el-radio>
              <el-radio value="hard">困难</el-radio>
            </el-radio-group>
          </div>

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1">
              题目数量：<span class="text-brand-600 font-bold">{{ form.count }}</span> 题
            </label>
            <el-slider v-model="form.count" :min="1" :max="20" :step="1" show-stops :marks="{ 5: '5', 10: '10', 15: '15', 20: '20' }" />
          </div>

          <div class="flex justify-end gap-3 pt-4">
            <el-button size="large" @click="$router.back()">返回</el-button>
            <el-button
              type="primary"
              size="large"
              class="!text-base !font-semibold !px-6"
              :loading="starting"
              :disabled="starting"
              @click="startExercise"
            >
              🚀 开始练习
            </el-button>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 阶段2：答题中 -->
    <div v-else-if="phase === 'taking'" class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-lg font-semibold text-slate-800">答题中</h2>
          <div class="flex items-center gap-3 text-sm text-slate-500">
            <span>第 {{ currentIndex + 1 }} / {{ exercise.questions.length }} 题</span>
            <span class="text-slate-300">|</span>
            <span class="font-mono">⏱ {{ formattedTime }}</span>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <div class="flex items-center gap-1.5 flex-wrap">
            <span class="text-xs text-slate-500 mr-1">答题进度</span>
            <button
              v-for="(q, idx) in exercise.questions"
              :key="q.id"
              class="w-9 h-9 md:w-8 md:h-8 rounded text-sm font-medium transition-all flex-shrink-0"
              :class="isAnswered(q.id)
                ? 'bg-green-500 text-white'
                : 'bg-slate-200 text-slate-500 hover:bg-slate-300'"
              :title="`第${idx+1}题`"
              @click="currentIndex = idx"
            >
              {{ idx + 1 }}
            </button>
          </div>
          <div class="text-sm text-slate-500">
            已答 <span class="text-brand-600 font-medium">{{ answeredCount }}</span> / {{ exercise.questions.length }}
          </div>
          <el-button
            type="primary"
            size="large"
            class="!text-base !font-semibold"
            :disabled="answeredCount < exercise.questions.length"
            @click="submitAll"
          >
            提交答案
          </el-button>
        </div>
      </div>

      <!-- 题目卡片 -->
      <el-card shadow="never" class="!border-slate-200" v-if="currentQuestion">
        <div class="space-y-5">
          <div class="flex items-start gap-3">
            <span class="text-lg font-bold text-brand-600 flex-shrink-0">Q{{ currentIndex + 1 }}</span>
            <div class="flex-1">
              <div class="text-sm text-slate-500 mb-1">{{ currentQuestion.knowledge_point }}</div>
              <div class="text-base text-slate-800 leading-relaxed">{{ currentQuestion.content }}</div>
            </div>
          </div>

          <div v-if="currentQuestion.question_type === 'true_false'" class="flex gap-4 pl-10">
            <label
              v-for="(opt, idx) in currentQuestion.options"
              :key="idx"
              class="flex-1 flex items-center justify-center gap-2 p-4 rounded-xl border-2 cursor-pointer transition-all text-base font-medium"
              :class="selectedAnswer === String.fromCharCode(65 + idx)
                ? 'border-green-500 bg-green-50 text-green-700'
                : 'border-slate-200 hover:border-green-300 hover:bg-green-50/50 text-slate-600'"
              @click="selectAnswer(String.fromCharCode(65 + idx))"
            >
              <span
                class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
                :class="selectedAnswer === String.fromCharCode(65 + idx)
                  ? 'bg-green-500 text-white'
                  : 'bg-slate-100 text-slate-500'"
              >
                {{ String.fromCharCode(65 + idx) }}
              </span>
              <span>{{ opt }}</span>
            </label>
          </div>
          <div v-else class="space-y-2.5 pl-10">
            <label
              v-for="(opt, idx) in currentQuestion.options"
              :key="idx"
              class="flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all"
              :class="selectedAnswer === String.fromCharCode(65 + idx)
                ? 'border-brand-500 bg-brand-50'
                : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'"
              @click="selectAnswer(String.fromCharCode(65 + idx))"
            >
              <span
                class="w-7 h-7 rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0"
                :class="selectedAnswer === String.fromCharCode(65 + idx)
                  ? 'bg-brand-500 text-white'
                  : 'bg-slate-100 text-slate-600'"
              >
                {{ String.fromCharCode(65 + idx) }}
              </span>
              <span class="text-sm text-slate-700">{{ opt.replace(/^[A-D]\.\s*/, "") }}</span>
            </label>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-slate-100">
            <el-tag :type="difficultyTagType(currentQuestion.difficulty)" size="small">
              {{ difficultyLabel(currentQuestion.difficulty) }}
            </el-tag>
            <div class="flex gap-2">
              <el-button
                :disabled="currentIndex === 0"
                @click="currentIndex--"
                size="default"
              >
                ⬅ 上一题
              </el-button>
              <el-button
                :disabled="currentIndex === exercise.questions.length - 1"
                @click="currentIndex++"
                size="default"
              >
                下一题 ➡
              </el-button>
              <el-button
                type="primary"
                size="default"
                :disabled="answeredCount < exercise.questions.length"
                @click="submitAll"
              >
                提交答案
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 阶段3：结果 -->
    <div v-else-if="phase === 'result'" class="space-y-6">
      <!-- 🎉 庆祝卡片：得分 + 用时 + 获得积分 + 新成就 -->
      <div class="rounded-2xl p-6 bg-gradient-to-br from-amber-50 via-white to-emerald-50 border-2 border-amber-200 shadow-soft">
        <div class="text-center">
          <div class="text-5xl mb-2">{{ resultEmoji }}</div>
          <h2 class="text-2xl font-bold text-slate-800">练习完成！</h2>
          <div class="mt-3">
            <span class="text-5xl font-bold" :class="scoreColor">{{ result.score }}</span>
            <span class="text-xl text-slate-500 ml-1">分</span>
          </div>
          <p class="text-sm text-slate-500 mt-1">
            答对 {{ result.correct_count }} / {{ result.total_questions }} 题
            <span v-if="result.time_spent" class="text-slate-400 ml-2">· 用时 {{ formatSeconds(result.time_spent) }}</span>
          </p>
        </div>

        <!-- 积分 + 成就行 -->
        <div v-if="result.points_earned > 0 || (result.new_achievements && result.new_achievements.length > 0)"
             class="mt-5 flex flex-wrap items-center justify-center gap-2">
          <span v-if="result.points_earned > 0"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-800 rounded-full text-sm font-medium border border-amber-300">
            🌟 获得 +{{ result.points_earned }} 积分
            <span class="text-xs text-amber-600 ml-1">（今日 {{ result.daily_points_total }}/{{ result.daily_points_cap }}）</span>
          </span>
          <span v-for="ach in (result.new_achievements || [])" :key="ach.id"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 text-purple-800 rounded-full text-sm font-medium border border-purple-300">
            {{ach.achievement?.icon || '🏆'}} {{ ach.achievement?.name || '解锁成就' }}
          </span>
        </div>
      </div>

      <!-- 得分条 -->
      <el-progress
        :percentage="result.score"
        :stroke-width="12"
        :color="score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'"
      />

      <!-- 逐题解析 -->
      <div class="space-y-3">
        <h3 class="text-sm font-semibold text-slate-700">📖 题目解析</h3>
        <div v-for="(q, idx) in resultQuestions" :key="q.id" class="card p-4">
          <div class="flex items-start gap-3">
            <span
              class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
              :class="q.is_correct ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
            >
              {{ q.is_correct ? '✓' : '✗' }}
            </span>
            <div class="flex-1">
              <div class="text-sm font-medium text-slate-800">{{ q.content }}</div>

              <!-- 选项列表 -->
              <div v-if="q.options && q.options.length" class="mt-2 space-y-1">
                <div
                  v-for="(opt, idx) in q.options"
                  :key="idx"
                  class="text-xs text-slate-600 flex items-center gap-1.5"
                >
                  <span
                    class="w-4 text-center font-medium"
                    :class="{
                      'text-green-600 font-bold': String.fromCharCode(65 + idx) === q.correct_answer,
                      'text-red-500 font-bold': String.fromCharCode(65 + idx) === q.selected && String.fromCharCode(65 + idx) !== q.correct_answer,
                    }"
                  >
                    {{ String.fromCharCode(65 + idx) }}.
                  </span>
                  <span
                    :class="{
                      'text-green-700': String.fromCharCode(65 + idx) === q.correct_answer,
                      'text-red-600 line-through': String.fromCharCode(65 + idx) === q.selected && String.fromCharCode(65 + idx) !== q.correct_answer,
                    }"
                  >
                    {{ opt.replace(/^[A-D]\.\s*/, '') }}
                  </span>
                </div>
              </div>

              <div class="mt-2 text-xs text-slate-500">
                <span class="text-slate-400">你的答案：</span>
                <span :class="q.is_correct ? 'text-green-600' : 'text-red-600'">{{ q.selected || '未作答' }}</span>
                <span class="mx-1.5 text-slate-300">|</span>
                <span class="text-slate-400">正确答案：</span>
                <span class="text-green-600">{{ q.correct_answer }}</span>
              </div>
              <div v-if="q.explanation" class="mt-2 text-xs text-slate-600 bg-slate-50 p-2 rounded">
                💡 {{ q.explanation }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="flex justify-center gap-3 pt-4">
        <el-button size="large" @click="$router.push('/question-banks')">返回题库</el-button>
        <el-button type="primary" size="large" class="!text-base !font-semibold !px-6" @click="restart">再来一组</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted, watch, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChildStore } from "@/stores/child";
import { questionBanksAPI } from "@/api";
import { ElMessage } from "element-plus";

const route = useRoute();
const router = useRouter();
const childStore = useChildStore();

const phase = ref("setup"); // setup / taking / result
const starting = ref(false);
const exercise = ref({ questions: [], answers: [], total_questions: 0 });
const currentIndex = ref(0);
const userAnswers = reactive({}); // { question_id: selected }
const result = ref(null);
const selectedAnswer = ref("");
// 知识点下拉引用：选择后自动收起（pad 友好，避免下拉挡住下一个按钮）
const kpSelectRef = ref(null);
function onKpChange() {
  // Element Plus el-select 默认多选不收起；调用 blur 手动收起。
  // setTimeout 延后一帧，确保选中的点击事件走完再失去焦点。
  setTimeout(() => kpSelectRef.value?.blur(), 0);
}

// 计时器
const elapsedSeconds = ref(0);
const formattedTime = computed(() => {
  const m = Math.floor(elapsedSeconds.value / 60)
    .toString()
    .padStart(2, "0");
  const s = (elapsedSeconds.value % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
});

function formatSeconds(sec) {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m === 0) return `${s} 秒`;
  return `${m} 分 ${s.toString().padStart(2, "0")} 秒`;
}
let timerInterval = null;
function startTimer() {
  stopTimer();
  elapsedSeconds.value = 0;
  timerInterval = setInterval(() => {
    elapsedSeconds.value += 1;
  }, 1000);
}
function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

const form = reactive({
  child_id: 0,
  bank_id: 0,
  count: 5,
  knowledge_points: [],
  difficulty: "",
  mode: "manual",
  wrong_question_ids: [],
});

// 从路由参数初始化
onMounted(async () => {
  const { bank_id, child_id, mode, knowledge_point, knowledge_points } = route.query;
  if (bank_id) form.bank_id = Number(bank_id);
  if (child_id) form.child_id = Number(child_id);
  if (mode) form.mode = mode;

  // 从路由参数读取知识点（支持单个或多个）
  if (knowledge_points) {
    form.knowledge_points = Array.isArray(knowledge_points) ? knowledge_points : knowledge_points.split(',');
  } else if (knowledge_point) {
    form.knowledge_points = [knowledge_point];
  }

  // 预加载该题库的知识点列表，方便选择器显示
  if (form.bank_id) {
    await loadKnowledgePoints();
  }

  // 如果是推荐模式且已有错题ID，自动开始
  if (form.mode === 'recommend' && form.bank_id) {
    loadRecommendation();
  }
});

async function loadRecommendation() {
  try {
    const data = await questionBanksAPI.recommend(form.child_id);
    if (data.wrong_questions && data.wrong_questions.length > 0) {
      form.wrong_question_ids = data.wrong_questions.map((w) => w.id);
      await startExercise();
    } else {
      ElMessage.info(data.suggestion || "暂无匹配的错题，请先去错题本录入");
    }
  } catch (e) {
    // handled
  }
}

const currentQuestion = computed(() => {
  if (!exercise.value.questions || currentIndex.value >= exercise.value.questions.length) return null;
  return exercise.value.questions[currentIndex.value];
});

watch(currentIndex, (idx) => {
  const qid = exercise.value.questions[idx]?.id;
  selectedAnswer.value = qid ? (userAnswers[qid] || "") : "";
});

const answeredCount = computed(() => Object.keys(userAnswers).length);

const progressPercent = computed(() => {
  if (!exercise.value.questions.length) return 0;
  return Math.round((answeredCount.value / exercise.value.questions.length) * 100);
});

const resultQuestions = computed(() => {
  if (!result.value || !exercise.value.questions) return [];
  const answerMap = {};
  for (const a of (result.value.answers || [])) {
    answerMap[a.question_id] = a;
  }
  return exercise.value.questions.map((q) => {
    const ans = answerMap[q.id] || {};
    return { ...q, ...ans };
  });
});

const resultEmoji = computed(() => {
  if (!result.value) return "";
  if (result.value.score >= 90) return "🎉";
  if (result.value.score >= 70) return "👍";
  if (result.value.score >= 60) return "😊";
  return "💪";
});

const scoreColor = computed(() => {
  if (!result.value) return "text-slate-800";
  if (result.value.score >= 80) return "text-green-600";
  if (result.value.score >= 60) return "text-amber-600";
  return "text-red-600";
});

const allKnowledgePoints = computed(() => {
  const set = new Set();
  if (exercise.value.questions) {
    for (const q of exercise.value.questions) {
      if (q.knowledge_point) set.add(q.knowledge_point);
    }
  }
  // 合并已加载的知识点，避免还没开始练习时选项为空
  for (const kp of availableKnowledgePoints.value) {
    if (kp) set.add(kp);
  }
  return Array.from(set).sort();
});

const availableKnowledgePoints = ref([]);
async function loadKnowledgePoints() {
  if (!form.bank_id) return;
  try {
    const questions = await questionBanksAPI.listQuestions(form.bank_id);
    const set = new Set();
    for (const q of questions) {
      if (q.knowledge_point) set.add(q.knowledge_point);
    }
    availableKnowledgePoints.value = Array.from(set).sort();
  } catch {
    // 加载失败不影响主流程，允许手动输入
  }
}

function isAnswered(qid) {
  return !!userAnswers[qid];
}

function selectAnswer(selected) {
  if (!currentQuestion.value) return;
  userAnswers[currentQuestion.value.id] = selected;
  selectedAnswer.value = selected;
}

async function startExercise() {
  if (!form.bank_id) {
    ElMessage.warning("请先选择题库");
    return;
  }
  if (!form.child_id) {
    form.child_id = childStore.current?.id || 0;
  }
  if (!form.child_id) {
    ElMessage.warning("请先选择孩子");
    return;
  }

  starting.value = true;
  try {
    const data = await questionBanksAPI.startExercise({
      child_id: form.child_id,
      bank_id: form.bank_id,
      count: form.count,
      knowledge_points: form.knowledge_points.length ? form.knowledge_points : undefined,
      difficulty: form.difficulty || undefined,
      mode: form.mode,
      wrong_question_ids: form.wrong_question_ids.length ? form.wrong_question_ids : undefined,
    });
    exercise.value = data;
    currentIndex.value = 0;
    phase.value = "taking";
    startTimer();
  } catch (e) {
    // handled
  } finally {
    starting.value = false;
  }
}

async function submitAll() {
  stopTimer();
  const answers = Object.entries(userAnswers).map(([question_id, selected]) => ({
    question_id: Number(question_id),
    selected,
  }));
  if (answers.length < exercise.value.questions.length) {
    ElMessage.warning(`还有 ${exercise.value.questions.length - answers.length} 题未作答`);
    return;
  }
  try {
    result.value = await questionBanksAPI.submitExercise(exercise.value.id, answers, elapsedSeconds.value);
    phase.value = "result";
  } catch (e) {
    // handled
  }
}

function restart() {
  stopTimer();
  phase.value = "setup";
  result.value = null;
  exercise.value = { questions: [], answers: [], total_questions: 0 };
  currentIndex.value = 0;
  selectedAnswer.value = "";
  elapsedSeconds.value = 0;
  Object.keys(userAnswers).forEach((k) => delete userAnswers[k]);
}

function difficultyTagType(d) {
  return d === "easy" ? "success" : d === "hard" ? "danger" : "warning";
}
function difficultyLabel(d) {
  return d === "easy" ? "简单" : d === "hard" ? "困难" : "中等";
}

onUnmounted(() => {
  stopTimer();
});
</script>

<style scoped>
</style>
