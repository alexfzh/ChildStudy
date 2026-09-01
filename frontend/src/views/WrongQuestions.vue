<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { wrongQuestionsAPI, questionBanksAPI } from "@/api";

const route = useRoute();
const router = useRouter();
const childStore = useChildStore();

const childId = computed(() => childStore.current?.id);
const loading = ref(false);
const items = ref([]);
const stats = ref(null);
const todayCount = ref(0);

const filters = ref({
  subject: "",
  mastery_level: "",
  status: "",
  keyword: "",
});

const masteryOptions = [
  { label: "新错题", value: "new" },
  { label: "学习中", value: "learning" },
  { label: "已掌握", value: "mastered" },
];

const statusOptions = [
  { label: "active", value: "active" },
  { label: "mastered", value: "mastered" },
  { label: "archived", value: "archived" },
];

const dialogVisible = ref(false);
const editing = ref(null);
const form = ref({
  subject: "",
  question_text: "",
  user_answer: "",
  correct_answer: "",
  error_reason: "careless",
  knowledge_points: [],
  knowledge_points_input: "",
  difficulty: "normal",
  note: "",
});

const reviewDialogVisible = ref(false);
const reviewTarget = ref(null);
const reviewResult = ref("correct");

const blankForm = () => ({
  subject: "",
  question_text: "",
  user_answer: "",
  correct_answer: "",
  error_reason: "careless",
  knowledge_points: [],
  knowledge_points_input: "",
  difficulty: "normal",
  note: "",
});

const fetchList = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    const params = {
      child_id: childId.value,
      ...(filters.value.subject && { subject: filters.value.subject }),
      ...(filters.value.mastery_level && { mastery_level: filters.value.mastery_level }),
      ...(filters.value.status && { status: filters.value.status }),
      ...(filters.value.keyword.trim() && { keyword: filters.value.keyword.trim() }),
    };
    items.value = await wrongQuestionsAPI.list(params);
  } finally {
    loading.value = false;
  }
};

const fetchStats = async () => {
  if (!childId.value) return;
  try {
    stats.value = await wrongQuestionsAPI.stats(childId.value);
  } catch (e) {
    stats.value = null;
  }
};

const fetchToday = async () => {
  if (!childId.value) return;
  try {
    const data = await wrongQuestionsAPI.today(childId.value);
    todayCount.value = data?.length || 0;
  } catch {
    todayCount.value = 0;
  }
};

onMounted(async () => {
  if (childId.value) {
    await Promise.all([fetchList(), fetchStats(), fetchToday()]);
  }
});

watch(childId, async (id) => {
  if (id) {
    await Promise.all([fetchList(), fetchStats(), fetchToday()]);
  }
});

const openCreate = () => {
  editing.value = null;
  form.value = blankForm();
  if (childStore.current?.subjects?.length) {
    form.value.subject = childStore.current.subjects[0];
  }
  dialogVisible.value = true;
};

const openEdit = (row) => {
  editing.value = row;
  form.value = {
    subject: row.subject || "",
    question_text: row.question_text || "",
    user_answer: row.user_answer || "",
    correct_answer: row.correct_answer || "",
    error_reason: row.error_reason || "careless",
    knowledge_points: row.knowledge_points || [],
    knowledge_points_input: (row.knowledge_points || []).join(", "),
    difficulty: row.difficulty || "normal",
    note: row.note || "",
  };
  dialogVisible.value = true;
};

const submit = async () => {
  if (!form.value.subject || !form.value.question_text.trim()) {
    ElMessage.warning("请填写科目和题目内容");
    return;
  }
  const payload = {
    ...form.value,
    knowledge_points: form.value.knowledge_points_input
      ? form.value.knowledge_points_input.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
      : [],
  };
  delete payload.knowledge_points_input;
  try {
    if (editing.value) {
      await wrongQuestionsAPI.update(editing.value.id, payload);
      ElMessage.success("已更新");
      dialogVisible.value = false;
      await fetchList();
      await fetchStats();
      await fetchToday();
    } else {
      const created = await wrongQuestionsAPI.create({
        ...payload,
        child_id: childId.value,
      });
      createdId.value = created.id;
      // 智能匹配：先不关闭 dialog，让用户看到分析结果
      await analyzeMatch(created.id);
    }
  } catch (e) {
    // axios interceptor 已提示
  }
};

// ============ 智能匹配 ============
const matchSuggestions = ref(null);
const analyzing = ref(false);
const createdId = ref(null);

const analyzeMatch = async (wqId) => {
  analyzing.value = true;
  try {
    const data = await wrongQuestionsAPI.match(wqId);
    matchSuggestions.value = data;
  } catch (e) {
    // 静默失败，不影响主流程
    matchSuggestions.value = null;
  } finally {
    analyzing.value = false;
  }
};

const applyMatch = async (wqId, suggestion) => {
  try {
    await wrongQuestionsAPI.applyMatch(wqId, {
      bank_question_id: suggestion.question_id,
      knowledge_points: suggestion.knowledge_points ? [suggestion.knowledge_points] : [],
    });
    ElMessage.success("已关联题库题目和知识点");
    matchSuggestions.value = null;
    dialogVisible.value = false;
    createdId.value = null;
    await fetchList();
    await fetchStats();
  } catch (e) {
    // handled
  }
};

const applyKPMatch = async (wqId, kp) => {
  try {
    const current = matchSuggestions.value;
    const kps = current?.kp_matches?.map((m) => m.name) || [];
    if (!kps.includes(kp.name)) kps.push(kp.name);
    await wrongQuestionsAPI.applyMatch(wqId, { knowledge_points: kps });
    ElMessage.success("已补全知识点");
    matchSuggestions.value = null;
    dialogVisible.value = false;
    createdId.value = null;
    await fetchList();
    await fetchStats();
  } catch (e) {
    // handled
  }
};

const ignoreMatch = async () => {
  matchSuggestions.value = null;
  dialogVisible.value = false;
  createdId.value = null;
  await fetchList();
  await fetchStats();
  await fetchToday();
};

const remove = async (row) => {
  await ElMessageBox.confirm(`确认删除这道错题吗？`, "删除", { type: "warning" });
  await wrongQuestionsAPI.remove(row.id);
  ElMessage.success("已删除");
  await fetchList();
  await fetchStats();
  await fetchToday();
};

const openReview = (row) => {
  reviewTarget.value = row;
  reviewResult.value = "correct";
  reviewDialogVisible.value = true;
};

const submitReview = async () => {
  if (!reviewTarget.value) return;
  try {
    await wrongQuestionsAPI.review(reviewTarget.value.id, reviewResult.value);
    ElMessage.success("复习记录已保存");
    reviewDialogVisible.value = false;
    reviewTarget.value = null;
    await fetchList();
    await fetchStats();
    await fetchToday();
  } catch (e) {
    // axios interceptor 已提示
  }
};

const subjectOptions = computed(() => {
  const set = new Set(["语文", "数学", "英语", "科学", "信息科技", "生物", "地理", "物理"]);
  (childStore.current?.subjects || []).forEach((s) => set.add(s));
  return Array.from(set);
});

const masteryLabel = (level) => {
  const map = { new: "新错题", learning: "学习中", mastered: "已掌握" };
  return map[level] || level;
};

const masteryTagType = (level) => {
  const map = { new: "danger", learning: "warning", mastered: "success" };
  return map[level] || "info";
};

const errorReasonLabel = (reason) => {
  const map = { careless: "粗心", concept: "概念不清", calculation: "计算错误", reasoning: "推理错误", unfamiliar: "题型陌生" };
  return map[reason] || reason || "未分类";
};

const nextReviewLabel = (row) => {
  if (!row.next_review_date) return "—";
  const today = new Date();
  const target = new Date(row.next_review_date);
  const diff = Math.ceil((target - today) / (1000 * 60 * 60 * 24));
  if (diff < 0) return `逾期${Math.abs(diff)}天`;
  if (diff === 0) return "今天";
  if (diff === 1) return "明天";
  return `${diff}天后`;
};

const goToExercise = async () => {
  if (!childId.value) return;
  try {
    const data = await questionBanksAPI.recommend(childId.value);
    if (data.matched_questions && data.matched_questions.length > 0) {
      const firstBankId = data.matched_questions[0].bank_id;
      router.push({
        name: "exercise",
        query: {
          bank_id: String(firstBankId),
          child_id: String(childId.value),
          mode: "recommend",
        },
      });
    } else {
      ElMessage.info(data.suggestion || "暂无匹配的练习题，请先去题库管理添加题目");
    }
  } catch (e) {
    // handled
  }
};
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">错题本</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录错题，艾宾浩斯复习提醒，把弱点逐个击破</p>
      </div>
      <button class="btn-primary" @click="openCreate" :disabled="!childId">+ 录入错题</button>
    </div>

    <!-- 统计卡 -->
    <div v-if="stats && childId" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      <div class="card p-4">
        <div class="text-xs text-slate-500">错题总数</div>
        <div class="text-2xl font-bold text-slate-800 mt-1">{{ stats.total || 0 }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">已掌握</div>
        <div class="text-2xl font-bold text-green-600 mt-1">{{ stats.mastered || 0 }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">掌握率</div>
        <div class="text-2xl font-bold text-brand-600 mt-1">{{ stats.mastery_rate ? `${stats.mastery_rate}%` : "0%" }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">今日待复习</div>
        <div class="text-2xl font-bold text-amber-600 mt-1">{{ todayCount }}</div>
      </div>
    </div>
    <!-- 去练习按钮 -->
    <div v-if="childId" class="mb-4">
      <el-button type="primary" @click="goToExercise" :disabled="!childId">
        ✏️ 根据错题推荐练习
      </el-button>
    </div>

    <!-- 筛选 -->
    <div class="card p-3 mb-4 flex gap-2 flex-wrap items-center">
      <el-select v-model="filters.subject" placeholder="全部科目" clearable size="default" class="!w-36">
        <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="filters.mastery_level" placeholder="掌握程度" clearable size="default" class="!w-32">
        <el-option v-for="item in masteryOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-select v-model="filters.status" placeholder="状态" clearable size="default" class="!w-28">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        placeholder="搜索题目或知识点..."
        clearable
        size="default"
        class="!w-56"
        @keyup.enter="fetchList"
      />
      <button class="btn-primary ml-auto" @click="fetchList">筛选</button>
    </div>

    <!-- 列表 -->
    <div v-if="!childId" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">👶</div>
      <div class="text-sm">请先在「孩子档案」中选择孩子</div>
    </div>
    <div v-else-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="items.length === 0" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">📙</div>
      <div class="text-sm">还没有错题，点击右上角录入</div>
    </div>
    <div v-else class="space-y-3">
      <div v-for="row in items" :key="row.id" class="card p-4 hover:border-brand-300 transition">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-xs font-medium px-2 py-0.5 rounded bg-brand-50 text-brand-700">{{ row.subject }}</span>
              <el-tag :type="masteryTagType(row.mastery_level)" size="small">{{ masteryLabel(row.mastery_level) }}</el-tag>
              <span class="text-xs text-slate-500">{{ errorReasonLabel(row.error_reason) }}</span>
              <span class="text-xs text-slate-400">复习{{ row.review_count || 0 }}次 · 错{{ row.wrong_count || 0 }}次</span>
            </div>
            <div class="mt-2 text-sm text-slate-800 line-clamp-2">{{ row.question_text }}</div>
            <div class="mt-2 text-xs text-slate-500">
              <span class="text-slate-400">你的答案：</span>{{ row.user_answer }}
              <span class="mx-1.5 text-slate-300">|</span>
              <span class="text-slate-400">正确答案：</span>{{ row.correct_answer }}
            </div>
            <div class="mt-2 flex flex-wrap gap-1">
              <span v-for="kp in (row.knowledge_points || [])" :key="kp" class="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{{ kp }}</span>
            </div>
            <div class="mt-1.5 text-xs text-slate-400">
              下次复习：{{ nextReviewLabel(row) }}
            </div>
          </div>
          <div class="flex flex-col gap-1.5 flex-shrink-0">
            <button class="text-xs text-brand-600 hover:text-brand-700" @click="openReview(row)">复习</button>
            <button class="text-xs text-slate-600 hover:text-slate-700" @click="openEdit(row)">编辑</button>
            <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(row)">删除</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 录入/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑错题' : '录入错题'" width="520px">
      <el-form label-position="top">
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="科目" required>
            <el-select v-model="form.subject" filterable allow-create class="w-full">
              <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
          <el-form-item label="难度">
            <el-select v-model="form.difficulty" class="w-full">
              <el-option label="简单" value="easy" />
              <el-option label="普通" value="normal" />
              <el-option label="困难" value="hard" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="题目内容" required>
          <el-input v-model="form.question_text" type="textarea" :rows="3" placeholder="粘贴题目..." />
        </el-form-item>
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="你的答案">
            <el-input v-model="form.user_answer" placeholder="你写的答案" />
          </el-form-item>
          <el-form-item label="正确答案">
            <el-input v-model="form.correct_answer" placeholder="正确答案" />
          </el-form-item>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="错因">
            <el-select v-model="form.error_reason" class="w-full">
              <el-option label="粗心" value="careless" />
              <el-option label="概念不清" value="concept" />
              <el-option label="计算错误" value="calculation" />
              <el-option label="推理错误" value="reasoning" />
              <el-option label="题型陌生" value="unfamiliar" />
            </el-select>
          </el-form-item>
          <el-form-item label="知识点（逗号分隔）">
            <el-input v-model="form.knowledge_points_input" placeholder="如：一元一次方程, 移项" />
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <!-- 智能分析卡片 -->
      <div v-if="matchSuggestions && !editing" class="mt-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-lg">🧠</span>
          <span class="font-semibold text-slate-800">智能分析</span>
          <span v-if="analyzing" class="text-xs text-slate-500">分析中...</span>
          <span v-else-if="matchSuggestions" class="text-xs text-green-600">分析完成</span>
        </div>

        <!-- 题库匹配 -->
        <div v-if="matchSuggestions.bank_matches && matchSuggestions.bank_matches.length" class="mb-3">
          <div class="text-xs text-slate-500 mb-1">🔗 可能来自题库：</div>
          <div v-for="m in matchSuggestions.bank_matches" :key="m.question_id" class="flex items-start justify-between gap-2 p-2 bg-white rounded border border-slate-200 mb-1.5">
            <div class="flex-1 min-w-0">
              <div class="text-xs font-medium text-slate-800 truncate">{{ m.bank_title }}</div>
              <div class="text-[10px] text-slate-500 mt-0.5 line-clamp-1">{{ m.content }}</div>
              <div class="flex gap-1 mt-1 flex-wrap">
                <span v-for="reason in m.match_reasons" :key="reason" class="text-[10px] px-1 rounded bg-blue-100 text-blue-700">{{ reason }}</span>
                <span class="text-[10px] px-1 rounded bg-slate-100 text-slate-600">相似度 {{ Math.round(m.score * 100) }}%</span>
              </div>
            </div>
            <button class="text-xs text-brand-600 hover:text-brand-700 whitespace-nowrap" @click="applyMatch(createdId.value, m)">
              采纳
            </button>
          </div>
        </div>

        <!-- 知识点匹配 -->
        <div v-if="matchSuggestions.kp_matches && matchSuggestions.kp_matches.length" class="mb-3">
          <div class="text-xs text-slate-500 mb-1">💡 推测知识点：</div>
          <div class="flex flex-wrap gap-1">
            <span v-for="m in matchSuggestions.kp_matches" :key="m.knowledge_point_id" class="text-xs px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 flex items-center gap-1">
              {{ m.name }}
              <span class="text-[10px] text-indigo-500">({{ Math.round(m.score * 100) }}%)</span>
              <button class="text-indigo-400 hover:text-indigo-600" @click="applyKPMatch(createdId.value, m)">+</button>
            </span>
          </div>
        </div>

        <div v-if="!matchSuggestions.bank_matches?.length && !matchSuggestions.kp_matches?.length" class="text-xs text-slate-500">
          暂无匹配建议，系统会持续学习优化
        </div>

        <div class="flex justify-end gap-2 mt-2">
          <button class="text-xs text-slate-500 hover:text-slate-700" @click="ignoreMatch">忽略建议</button>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>

    <!-- 复习 -->
    <el-dialog v-model="reviewDialogVisible" title="复习" width="420px">
      <div v-if="reviewTarget" class="mb-4">
        <div class="text-sm text-slate-600 mb-2">{{ reviewTarget.subject }} · {{ reviewTarget.question_text }}</div>
        <div class="text-xs text-slate-500">正确答案：{{ reviewTarget.correct_answer }}</div>
      </div>
      <div class="text-sm text-slate-700 mb-2">这次复习结果：</div>
      <el-radio-group v-model="reviewResult" class="flex flex-col gap-2">
        <el-radio value="correct">✅ 做对了</el-radio>
        <el-radio value="partial">🤔 半对 / 思路对但结果错</el-radio>
        <el-radio value="wrong">❌ 还是不会</el-radio>
      </el-radio-group>
      <template #footer>
        <button class="btn-ghost" @click="reviewDialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submitReview">保存复习</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
