<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";
import { useChildStore } from "@/stores/child";
import { homeworksAPI, importExportAPI } from "@/api";
import { PRESET_SUBJECTS } from "@/constants/subjects";

const childStore = useChildStore();

const loading = ref(false);
const homeworks = ref([]);
const filterSubject = ref("");

const blank = () => ({
  child_id: childStore.currentId,
  subject: "",
  title: "",
  homework_date: dayjs().format("YYYY-MM-DD"),
  duration_minutes: null,
  total_questions: null,
  correct_questions: null,
  accuracy: null,
  completed: true,
  difficulty: "normal",
  note: "",
});

const form = ref(blank());
const dialogVisible = ref(false);
const editing = ref(null);

// ============ 行内编辑 ============
const editingCell = ref(null); // { rowId: number, field: string } | null

const isEditing = (row, field) => editingCell.value?.rowId === row.id && editingCell.value?.field === field

const startEdit = (row, field) => {
  editingCell.value = { rowId: row.id, field };
};
const saveEdit = async (row, field, value) => {
  const prev = editingCell.value;
  editingCell.value = null;
  try {
    await homeworksAPI.update(row.id, { [field]: value });
    Object.assign(row, { [field]: value });
    ElMessage.success("已更新");
  } catch {
    editingCell.value = prev;
  }
};
const cancelEdit = () => {
  editingCell.value = null;
};

const fetchList = async () => {
  if (!childStore.currentId) return;
  loading.value = true;
  try {
    homeworks.value = await homeworksAPI.list({
      child_id: childStore.currentId,
      subject: filterSubject.value || undefined,
    });
  } finally {
    loading.value = false;
  }
};

onMounted(fetchList);
watch(() => childStore.currentId, fetchList);
watch(filterSubject, fetchList);

const openCreate = () => {
  editing.value = null;
  form.value = blank();
  dialogVisible.value = true;
};
const openEdit = (h) => {
  editing.value = h;
  form.value = { ...blank(), ...h };
  dialogVisible.value = true;
};

const submit = async () => {
  if (!form.value.subject || !form.value.title) {
    ElMessage.warning("请填写科目和作业标题");
    return;
  }
  if (editing.value) {
    await homeworksAPI.update(editing.value.id, form.value);
    ElMessage.success("已更新");
  } else {
    await homeworksAPI.create(form.value);
    ElMessage.success("已录入");
  }
  dialogVisible.value = false;
  await fetchList();
};

const remove = async (h) => {
  await ElMessageBox.confirm(`确认删除「${h.title}」吗？`, "删除", { type: "warning" });
  await homeworksAPI.remove(h.id);
  ElMessage.success("已删除");
  await fetchList();
};

const subjectOptions = computed(() => {
  const set = new Set(PRESET_SUBJECTS);
  (childStore.current?.subjects || []).forEach((s) => set.add(s));
  homeworks.value.forEach((h) => set.add(h.subject));
  return Array.from(set).sort();
});

const accColor = (a) => a == null ? "text-slate-400" : a >= 90 ? "text-emerald-600" : a >= 75 ? "text-brand-600" : a >= 60 ? "text-amber-600" : "text-rose-600";

const difficultyLabel = (d) => ({ easy: "简单", normal: "中等", hard: "困难" })[d] || d;
const difficultyBadge = (d) => d === "easy" ? "badge-info" : d === "hard" ? "badge-down" : "badge-flat";

// ============ 导入导出 ============
const importDialogVisible = ref(false);
const importFile = ref(null);
const importLoading = ref(false);

const doExport = async () => {
  try {
    const blob = await importExportAPI.exportHomeworks({
      child_id: childStore.currentId,
      subject: filterSubject.value || undefined,
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `homeworks_${childStore.current?.name || "all"}_${dayjs().format("YYYYMMDD")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("导出成功");
  } catch (e) { /* axios 已提示 */ }
};

const doImport = async () => {
  if (!importFile.value) {
    ElMessage.warning("请选择 CSV 文件");
    return;
  }
  importLoading.value = true;
  try {
    const res = await importExportAPI.importHomeworks(importFile.value, childStore.currentId);
    ElMessage.success(res.message || "导入完成");
    importDialogVisible.value = false;
    importFile.value = null;
    await fetchList();
  } catch (e) { /* axios 已提示 */ }
  finally {
    importLoading.value = false;
  }
};
</script>

<template>
  <div v-if="!childStore.currentId" class="card p-10 text-center text-slate-500">
    请先在「孩子档案」中添加孩子
  </div>

  <div v-else>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">作业追踪</h2>
        <p class="text-sm text-slate-500 mt-0.5">日常练习的完成情况与正确率</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="doExport">📥 导出 CSV</button>
        <button class="btn-secondary" @click="importDialogVisible = true">📤 导入 CSV</button>
        <button class="btn-primary" @click="openCreate">+ 录入作业</button>
      </div>
    </div>

    <div class="card p-3 mb-4">
      <el-select v-model="filterSubject" placeholder="全部科目" clearable class="!w-40">
        <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
      </el-select>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="homeworks.length === 0" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">📚</div>
      <div class="text-sm">还没有作业记录</div>
    </div>

    <div v-else class="card p-0 overflow-hidden">
      <el-table :data="homeworks" style="width: 100%">
        <el-table-column prop="homework_date" label="日期" width="120" sortable>
          <template #default="scope">
            {{ dayjs(scope.row.homework_date).format('MM-DD') }}
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="科目" width="100" sortable>
          <template #default="scope">
            <el-select
              v-if="isEditing(scope.row, 'subject')"
              :model-value="scope.row.subject"
              size="small"
              @change="saveEdit(scope.row, 'subject', $event)"
              @blur="saveEdit(scope.row, 'subject', scope.row.subject)"
              @keyup.enter="$event.target.blur()"
            >
              <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
            </el-select>
            <span
              v-else
              class="badge bg-slate-100 text-slate-600 cursor-pointer hover:opacity-70"
              @dblclick="startEdit(scope.row, 'subject')"
            >{{ scope.row.subject }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="180" show-overflow-tooltip sortable>
          <template #default="scope">
            <el-input
              v-if="isEditing(scope.row, 'title')"
              :model-value="scope.row.title"
              size="small"
              @blur="saveEdit(scope.row, 'title', scope.row.title)"
              @keyup.enter="$event.target.blur()"
            />
            <span
              v-else
              class="cursor-pointer hover:text-brand-600"
              @dblclick="startEdit(scope.row, 'title')"
            >{{ scope.row.title }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="accuracy" label="正确率" width="110" align="center" sortable>
          <template #default="scope">
            <el-input-number
              v-if="isEditing(scope.row, 'accuracy')"
              :model-value="scope.row.accuracy"
              :precision="1"
              :min="0"
              :max="100"
              size="small"
              controls-position="right"
              @blur="saveEdit(scope.row, 'accuracy', scope.row.accuracy)"
              @keyup.enter="$event.target.blur()"
            />
            <span
              v-else
              :class="['cursor-pointer', accColor(scope.row.accuracy)]"
              @dblclick="startEdit(scope.row, 'accuracy')"
            >
              {{ scope.row.accuracy != null ? scope.row.accuracy + '%' : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_questions" label="题量" width="110" align="center" sortable>
          <template #default="scope">
            <el-input-number
              v-if="isEditing(scope.row, 'total_questions')"
              :model-value="scope.row.total_questions"
              :min="0"
              size="small"
              controls-position="right"
              @blur="saveEdit(scope.row, 'total_questions', scope.row.total_questions)"
              @keyup.enter="$event.target.blur()"
            />
            <span
              v-else
              class="cursor-pointer hover:text-brand-600"
              @dblclick="startEdit(scope.row, 'total_questions')"
            >
              {{ scope.row.total_questions ?? '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="difficulty" label="难度" width="90" align="center" sortable>
          <template #default="scope">
            <el-select
              v-if="isEditing(scope.row, 'difficulty')"
              :model-value="scope.row.difficulty"
              size="small"
              @change="saveEdit(scope.row, 'difficulty', $event)"
              @blur="saveEdit(scope.row, 'difficulty', scope.row.difficulty)"
              @keyup.enter="$event.target.blur()"
            >
              <el-option label="简单" value="easy" />
              <el-option label="中等" value="normal" />
              <el-option label="困难" value="hard" />
            </el-select>
            <span
              v-else
              class="cursor-pointer"
              :class="difficultyBadge(scope.row.difficulty)"
              @dblclick="startEdit(scope.row, 'difficulty')"
            >{{ difficultyLabel(scope.row.difficulty) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="completed" label="完成" width="80" align="center" sortable>
          <template #default="scope">
            <el-select
              v-if="isEditing(scope.row, 'completed')"
              :model-value="scope.row.completed"
              size="small"
              @change="saveEdit(scope.row, 'completed', $event)"
              @blur="saveEdit(scope.row, 'completed', scope.row.completed)"
              @keyup.enter="$event.target.blur()"
            >
              <el-option label="✓ 完成" :value="true" />
              <el-option label="○ 未完成" :value="false" />
            </el-select>
            <span
              v-else
              class="cursor-pointer"
              :class="scope.row.completed ? 'text-emerald-600' : 'text-amber-600'"
              @dblclick="startEdit(scope.row, 'completed')"
            >{{ scope.row.completed ? '✓' : '○' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right" align="center">
          <template #default="scope">
            <button class="btn-ghost text-xs" @click="openEdit(scope.row)">编辑</button>
            <button class="btn-ghost text-xs text-rose-600" @click="remove(scope.row)">删除</button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 表单对话框 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑作业' : '录入作业'" width="520px">
      <el-form label-position="top">
        <el-form-item label="科目" required>
          <el-select v-model="form.subject" filterable placeholder="从下拉选，不能新建" class="w-full">
            <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
          </el-select>
          <div class="text-xs text-slate-400 mt-1">
            💡 仅显示预设 + 你在孩子档案里选过的科目。新增科目请去「孩子档案」编辑
          </div>
        </el-form-item>
        <el-form-item label="作业标题" required>
          <el-input v-model="form.title" placeholder="如：练习册第12页" />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="form.homework_date" value-format="YYYY-MM-DD" type="date" class="w-full" />
        </el-form-item>
        <div class="grid grid-cols-3 gap-3">
          <el-form-item label="用时(分钟)">
            <el-input-number v-model="form.duration_minutes" :min="0" class="!w-full" />
          </el-form-item>
          <el-form-item label="总题数">
            <el-input-number v-model="form.total_questions" :min="0" class="!w-full" />
          </el-form-item>
          <el-form-item label="正确题数">
            <el-input-number v-model="form.correct_questions" :min="0" class="!w-full" />
          </el-form-item>
        </div>
        <el-form-item label="难度">
          <el-radio-group v-model="form.difficulty">
            <el-radio value="easy">简单</el-radio>
            <el-radio value="normal">中等</el-radio>
            <el-radio value="hard">困难</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="完成情况">
          <el-switch v-model="form.completed" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入作业 CSV" width="480px">
      <div class="space-y-3">
        <div class="text-sm text-slate-600">
          当前孩子：<span class="font-medium">{{ childStore.current?.name }}</span>（{{ childStore.current?.grade }}）
        </div>
        <el-alert title="CSV 必须包含列：subject, title, homework_date" type="info" :closable="false" />
        <el-form label-position="top">
          <el-form-item label="选择 CSV 文件">
            <input type="file" accept=".csv" @change="(e) => importFile.value = e.target.files[0]" />
          </el-form-item>
        </el-form>
        <div class="text-xs text-slate-400">
          💡 先点击「导出 CSV」下载模板，按格式填写后上传。系统会自动按当前孩子导入。
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="importDialogVisible = false">取消</button>
        <button class="btn-primary ml-2" :loading="importLoading" @click="doImport">开始导入</button>
      </template>
    </el-dialog>
  </div>
</template>
