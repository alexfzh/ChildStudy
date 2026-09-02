<template>
  <div class="space-y-6">
    <!-- 头部 -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">✏️ 题库练习</h1>
        <p class="text-sm text-slate-500 mt-1">管理题目、组卷出题、巩固薄弱知识点</p>
      </div>
      <el-button type="primary" @click="showCreateBankDialog = true">
        <span class="mr-1">+</span> 新建题库
      </el-button>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="!border-slate-200">
      <div class="flex flex-wrap items-center gap-3">
        <el-select
          v-model="filterGrade"
          placeholder="选择年级"
          clearable
          class="!w-36"
          @change="fetchBanks"
        >
          <el-option label="四年级" value="四年级" />
          <el-option label="五年级" value="五年级" />
          <el-option label="六年级" value="六年级" />
          <el-option label="初一" value="初一" />
          <el-option label="初二" value="初二" />
          <el-option label="初三" value="初三" />
        </el-select>
        <el-select
          v-model="filterSubject"
          placeholder="选择科目"
          clearable
          class="!w-36"
          @change="fetchBanks"
        >
          <el-option label="英语" value="英语" />
          <el-option label="数学" value="数学" />
          <el-option label="语文" value="语文" />
          <el-option label="科学" value="科学" />
        </el-select>
        <el-button
          :type="selectedBank ? 'primary' : 'info'"
          :plain="!selectedBank"
          :disabled="!selectedBank"
          size="large"
          class="!text-base !px-5 !py-2"
          @click="goToExercise"
        >
          <span v-if="selectedBank">🚀 去练习「{{ selectedBank.title }}」</span>
          <span v-else>🚀 去练习（请先选中一个题库）</span>
        </el-button>
      </div>
    </el-card>

    <!-- 题库列表 -->
    <div v-loading="loading" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <el-card
        v-for="bank in banks"
        :key="bank.id"
        shadow="hover"
        class="cursor-pointer transition-all"
        :class="selectedBank?.id === bank.id ? '!border-brand-500 ring-2 ring-brand-200' : '!border-slate-200'"
        @click="selectBank(bank)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 mb-2">
              <span class="text-lg font-semibold text-slate-800 truncate">{{ bank.title }}</span>
              <el-tag v-if="!bank.is_active" type="info" size="small">未启用</el-tag>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-500 mb-2">
              <el-tag size="small" type="success">{{ bank.grade }}</el-tag>
              <el-tag size="small" type="warning">{{ bank.subject }}</el-tag>
            </div>
            <p class="text-sm text-slate-500 line-clamp-2">{{ bank.description || "暂无描述" }}</p>
            <div class="mt-3 text-xs text-slate-400">
              共 <span class="text-brand-600 font-medium">{{ bank.question_count }}</span> 道题
            </div>
            <!-- 卡内一键开始按钮（pad 上最明显的一键入口） -->
            <el-button
              type="primary"
              size="large"
              class="!w-full !mt-3 !text-base !font-semibold !min-h-[48px]"
              @click.stop="selectAndGoExercise(bank)"
            >
              🚀 开始练习
            </el-button>
          </div>
          <div class="flex flex-col gap-1.5 ml-3">
            <el-button size="default" @click.stop="editBank(bank)">编辑</el-button>
            <el-button size="default" type="danger" @click.stop="deleteBank(bank)">删除</el-button>
          </div>
        </div>
      </el-card>
    </div>

    <el-empty v-if="!loading && banks.length === 0" description="暂无题库，点击右上角创建" />

    <!-- 题目管理（选中题库后显示） -->
    <div v-if="selectedBank" class="mt-8">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-slate-800">
          📝 {{ selectedBank.title }} - 题目管理
        </h2>
        <el-button type="primary" @click="showCreateQuestionDialog = true">
          <span class="mr-1">+</span> 添加题目
        </el-button>
      </div>

      <!-- 题目统计（可点击跳转到练习，pad 上足够大的点击区域） -->
      <div class="flex flex-wrap gap-2 mb-4">
        <button
          v-for="(cnt, kp) in questionStats"
          :key="kp"
          type="button"
          class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-slate-100 hover:bg-brand-50 hover:text-brand-700 hover:border-brand-300 border border-slate-200 text-slate-700 text-sm font-medium transition-colors cursor-pointer"
          @click.stop="goToExerciseWithKP(kp)"
        >
          <span>📚 {{ kp }}</span>
          <span class="text-xs opacity-70">· {{ cnt }} 题</span>
          <span class="text-xs">🚀</span>
        </button>
      </div>

      <!-- 题目列表 -->
      <el-table :data="questions" stripe border class="!w-full" v-loading="qLoading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="question_type" label="题型" width="80">
          <template #default="{ row }">
            <el-tag :type="row.question_type === 'true_false' ? 'warning' : 'primary'" size="small">
              {{ row.question_type === 'true_false' ? '判断' : '单选' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="knowledge_point" label="知识点" width="140" />
        <el-table-column prop="difficulty" label="难度" width="80">
          <template #default="{ row }">
            <el-tag :type="difficultyType(row.difficulty)" size="small">
              {{ difficultyLabel(row.difficulty) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="题干" show-overflow-tooltip min-width="200" />
        <el-table-column label="选项" width="200">
          <template #default="{ row }">
            <span class="text-xs text-slate-500">{{ row.options.join(' / ') }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="correct_answer" label="答案" width="60">
          <template #default="{ row }">
            <el-tag type="success" size="small">{{ row.correct_answer }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="editQuestion(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteQuestion(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建/编辑题库弹窗 -->
    <el-dialog v-model="showCreateBankDialog" :title="editingBank ? '编辑题库' : '新建题库'" width="500px">
      <el-form :model="bankForm" label-width="100px">
        <el-form-item label="年级" required>
          <el-select v-model="bankForm.grade" class="!w-full">
            <el-option label="四年级" value="四年级" />
            <el-option label="五年级" value="五年级" />
            <el-option label="六年级" value="六年级" />
            <el-option label="初一" value="初一" />
            <el-option label="初二" value="初二" />
            <el-option label="初三" value="初三" />
          </el-select>
        </el-form-item>
        <el-form-item label="科目" required>
          <el-select v-model="bankForm.subject" class="!w-full">
            <el-option label="英语" value="英语" />
            <el-option label="数学" value="数学" />
            <el-option label="语文" value="语文" />
            <el-option label="科学" value="科学" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="bankForm.title" placeholder="如：上海牛津版四年级英语" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="bankForm.description" type="textarea" :rows="3" placeholder="题库描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateBankDialog = false">取消</el-button>
        <el-button type="primary" @click="saveBank">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新建/编辑题目弹窗 -->
    <el-dialog v-model="showCreateQuestionDialog" :title="editingQuestion ? '编辑题目' : '添加题目'" width="600px">
      <el-form :model="questionForm" label-width="120px">
        <el-form-item label="知识点" required>
          <el-input v-model="questionForm.knowledge_point" placeholder="如：现在进行时" />
        </el-form-item>
        <el-form-item label="题型" required>
          <el-radio-group v-model="questionForm.question_type" @change="onQuestionTypeChange">
            <el-radio value="single_choice">单选题</el-radio>
            <el-radio value="true_false">判断题</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="难度" required>
          <el-select v-model="questionForm.difficulty" class="!w-full">
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="normal" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="题干" required>
          <el-input v-model="questionForm.content" type="textarea" :rows="3" placeholder="题目内容" />
        </el-form-item>
        <el-form-item label="选项" required>
          <template v-if="questionForm.question_type === 'true_false'">
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 text-sm font-medium text-slate-500">A.</span>
              <el-input value="正确" disabled class="!flex-1" />
            </div>
            <div class="flex items-center gap-2 mb-2">
              <span class="w-6 text-sm font-medium text-slate-500">B.</span>
              <el-input value="错误" disabled class="!flex-1" />
            </div>
          </template>
          <div v-for="(opt, idx) in questionForm.options" v-else :key="idx" class="flex items-center gap-2 mb-2">
            <span class="w-6 text-sm font-medium text-slate-500">{{ String.fromCharCode(65 + idx) }}.</span>
            <el-input v-model="questionForm.options[idx]" placeholder="选项内容" class="!flex-1" />
          </div>
        </el-form-item>
        <el-form-item label="正确答案" required>
          <el-radio-group v-model="questionForm.correct_answer">
            <el-radio v-if="questionForm.question_type === 'true_false'" value="A">A. 正确</el-radio>
            <el-radio v-if="questionForm.question_type === 'true_false'" value="B">B. 错误</el-radio>
            <template v-else>
              <el-radio v-for="(opt, idx) in questionForm.options" :key="idx" :value="String.fromCharCode(65 + idx)">
                {{ String.fromCharCode(65 + idx) }}
              </el-radio>
            </template>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="解析">
          <el-input v-model="questionForm.explanation" type="textarea" :rows="3" placeholder="答案解释（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateQuestionDialog = false">取消</el-button>
        <el-button type="primary" @click="saveQuestion">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChildStore } from "@/stores/child";
import { questionBanksAPI } from "@/api";
import { ElMessage, ElMessageBox } from "element-plus";

const route = useRoute();
const router = useRouter();
const childStore = useChildStore();

const loading = ref(false);
const qLoading = ref(false);
const banks = ref([]);
const questions = ref([]);
const filterGrade = ref("");
const filterSubject = ref("");
const selectedBank = ref(null);

// 题库表单
const showCreateBankDialog = ref(false);
const editingBank = ref(null);
const bankForm = reactive({
  grade: "四年级",
  subject: "英语",
  title: "",
  description: "",
  is_active: true,
});

// 题目表单
const showCreateQuestionDialog = ref(false);
const editingQuestion = ref(null);
const questionForm = reactive({
  bank_id: 0,
  knowledge_point: "",
  question_type: "single_choice",
  difficulty: "normal",
  content: "",
  options: ["", "", "", ""],
  correct_answer: "A",
  explanation: "",
});

function onQuestionTypeChange() {
  if (questionForm.question_type === "true_false") {
    questionForm.options = ["正确", "错误", "", ""];
    questionForm.correct_answer = "A";
  } else {
    questionForm.options = ["", "", "", ""];
    questionForm.correct_answer = "A";
  }
}

// 知识点统计
const questionStats = computed(() => {
  const stats = {};
  for (const q of questions.value) {
    stats[q.knowledge_point] = (stats[q.knowledge_point] || 0) + 1;
  }
  return stats;
});

async function fetchBanks() {
  loading.value = true;
  try {
    const params = {};
    if (filterGrade.value) params.grade = filterGrade.value;
    if (filterSubject.value) params.subject = filterSubject.value;
    banks.value = await questionBanksAPI.list(params);
  } finally {
    loading.value = false;
  }
}

function selectBank(bank) {
  selectedBank.value = bank;
  fetchQuestions(bank.id);
}

// 一键选中 + 去练习（题库卡片里的快速入口，跳过手动选中这一步）
function selectAndGoExercise(bank) {
  selectBank(bank);
  const childId = childStore.current?.id;
  if (!childId) {
    ElMessage.warning("请先选择孩子");
    return;
  }
  router.push({
    name: "exercise",
    query: { bank_id: bank.id, child_id: childId },
  });
}

async function fetchQuestions(bankId) {
  qLoading.value = true;
  try {
    questions.value = await questionBanksAPI.listQuestions(bankId);
  } finally {
    qLoading.value = false;
  }
}

function goToExerciseWithKP(kp) {
  if (!selectedBank.value) return;
  const childId = childStore.current?.id;
  if (!childId) {
    ElMessage.warning("请先选择孩子");
    return;
  }
  router.push({
    name: "exercise",
    query: {
      bank_id: selectedBank.value.id,
      child_id: childId,
      knowledge_point: kp,
    },
  });
}

function goToExercise() {
  if (!selectedBank.value) return;
  const childId = childStore.current?.id;
  if (!childId) {
    ElMessage.warning("请先选择孩子");
    return;
  }
  router.push({
    name: "exercise",
    query: { bank_id: selectedBank.value.id, child_id: childId },
  });
}

function editBank(bank) {
  editingBank.value = bank;
  bankForm.grade = bank.grade;
  bankForm.subject = bank.subject;
  bankForm.title = bank.title;
  bankForm.description = bank.description || "";
  bankForm.is_active = bank.is_active;
  showCreateBankDialog.value = true;
}

async function saveBank() {
  try {
    if (editingBank.value) {
      await questionBanksAPI.update(editingBank.value.id, bankForm);
      ElMessage.success("更新成功");
    } else {
      await questionBanksAPI.create(bankForm);
      ElMessage.success("创建成功");
    }
    showCreateBankDialog.value = false;
    editingBank.value = null;
    fetchBanks();
  } catch (e) {
    // handled by interceptor
  }
}

async function deleteBank(bank) {
  try {
    await ElMessageBox.confirm(`确定删除题库「${bank.title}」？题目也会被删除。`, "确认删除", {
      type: "warning",
    });
    await questionBanksAPI.remove(bank.id);
    ElMessage.success("删除成功");
    if (selectedBank.value?.id === bank.id) {
      selectedBank.value = null;
      questions.value = [];
    }
    fetchBanks();
  } catch {
    // cancelled
  }
}

function editQuestion(q) {
  editingQuestion.value = q;
  questionForm.bank_id = q.bank_id;
  questionForm.knowledge_point = q.knowledge_point;
  questionForm.question_type = q.question_type || "single_choice";
  questionForm.difficulty = q.difficulty;
  questionForm.content = q.content;
  questionForm.options = [...q.options];
  questionForm.correct_answer = q.correct_answer;
  questionForm.explanation = q.explanation || "";
  showCreateQuestionDialog.value = true;
}

async function saveQuestion() {
  try {
    if (editingQuestion.value) {
      await questionBanksAPI.updateQuestion(selectedBank.value.id, editingQuestion.value.id, questionForm);
      ElMessage.success("更新成功");
    } else {
      await questionBanksAPI.createQuestion(selectedBank.value.id, questionForm);
      ElMessage.success("添加成功");
    }
    showCreateQuestionDialog.value = false;
    editingQuestion.value = null;
    resetQuestionForm();
    fetchQuestions(selectedBank.value.id);
  } catch {
    // handled
  }
}

async function deleteQuestion(q) {
  try {
    await ElMessageBox.confirm("确定删除这道题？", "确认删除", { type: "warning" });
    await questionBanksAPI.deleteQuestion(selectedBank.value.id, q.id);
    ElMessage.success("删除成功");
    fetchQuestions(selectedBank.value.id);
  } catch {
    // cancelled
  }
}

function resetQuestionForm() {
  questionForm.knowledge_point = "";
  questionForm.question_type = "single_choice";
  questionForm.difficulty = "normal";
  questionForm.content = "";
  questionForm.options = ["", "", "", ""];
  questionForm.correct_answer = "A";
  questionForm.explanation = "";
}

function difficultyType(d) {
  return d === "easy" ? "success" : d === "hard" ? "danger" : "warning";
}
function difficultyLabel(d) {
  return d === "easy" ? "简单" : d === "hard" ? "困难" : "中等";
}

onMounted(() => {
  fetchBanks();
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
