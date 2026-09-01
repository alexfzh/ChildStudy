<script setup>
import { ref, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { knowledgePointsAPI } from "@/api";
import { SUBJECT_COLOR_MAP, CUSTOM_SUBJECT_COLOR } from "@/constants/subjects";

const childStore = useChildStore();

// 按科目给标签上色：科目色描边 + 同色浅底 + 同色深字（自定义科目用中性灰）
const subjectChipClass = (subject) =>
  SUBJECT_COLOR_MAP[subject] || CUSTOM_SUBJECT_COLOR;

// 从配色串里取 text-* 类，给科目分组标题上色
const subjectTextClass = (subject) =>
  (SUBJECT_COLOR_MAP[subject] || CUSTOM_SUBJECT_COLOR)
    .split(" ")
    .find((c) => c.startsWith("text-")) || "text-slate-600";

const loading = ref(false);
const points = ref([]);
const filterSubject = ref("");
const filterCategory = ref("");
const filterGradeLevel = ref("");
const searchKeyword = ref("");

const gradeLevelOptions = ref([]);

const dialogVisible = ref(false);
const editing = ref(null);

const blank = () => ({
  subject: childStore.current?.subjects?.[0] || "",
  name: "",
  category: "",
  description: "",
  grade_level: "",
});

const form = ref(blank());

const fetchList = async () => {
  loading.value = true;
  try {
    points.value = await knowledgePointsAPI.list({
      subject: filterSubject.value || undefined,
      category: filterCategory.value || undefined,
      grade_level: filterGradeLevel.value || undefined,
      keyword: searchKeyword.value.trim() || undefined,
    });
  } finally {
    loading.value = false;
  }
};

const fetchGradeLevels = async () => {
  try {
    gradeLevelOptions.value = await knowledgePointsAPI.listGradeLevels();
  } catch {
    gradeLevelOptions.value = [];
  }
};

onMounted(async () => {
  await Promise.all([fetchList(), fetchGradeLevels()]);
});

const openCreate = () => {
  editing.value = null;
  form.value = blank();
  dialogVisible.value = true;
};

const openEdit = (p) => {
  editing.value = p;
  form.value = { ...blank(), ...p };
  dialogVisible.value = true;
};

const submit = async () => {
  if (!form.value.subject || !form.value.name.trim()) {
    ElMessage.warning("请填写科目和知识点名称");
    return;
  }
  try {
    if (editing.value) {
      await knowledgePointsAPI.update(editing.value.id, form.value);
      ElMessage.success("已更新");
    } else {
      await knowledgePointsAPI.create(form.value);
      ElMessage.success("已添加");
    }
    dialogVisible.value = false;
    await fetchList();
  } catch (e) { /* axios 已提示 */ }
};

const remove = async (p) => {
  await ElMessageBox.confirm(`确认删除知识点「${p.name}」吗？`, "删除", { type: "warning" });
  await knowledgePointsAPI.remove(p.id);
  ElMessage.success("已删除");
  await fetchList();
};

const subjectOptions = computed(() => {
  const set = new Set(["语文", "数学", "英语", "科学", "信息科技", "生物", "地理", "物理"]);
  (childStore.current?.subjects || []).forEach((s) => set.add(s));
  return Array.from(set);
});

const grouped = () => {
  const groups = {};
  points.value.forEach((p) => {
    const grade = p.grade_level || "未分年级";
    const subject = p.subject || "未分类";
    if (!groups[grade]) groups[grade] = {};
    if (!groups[grade][subject]) groups[grade][subject] = [];
    groups[grade][subject].push(p);
  });
  return groups;
  
};
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">知识点标签库</h2>
        <p class="text-sm text-slate-500 mt-0.5">统一管理各科知识点，录入考试时可直接选用</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 添加知识点</button>
    </div>

    <!-- 筛选 -->
    <div class="card p-3 mb-4 flex gap-2 flex-wrap items-center">
      <el-select v-model="filterSubject" placeholder="全部科目" clearable size="default" class="!w-36" @change="fetchList">
        <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="filterGradeLevel" placeholder="全部年级" clearable size="default" class="!w-32" @change="fetchList">
        <el-option v-for="g in gradeLevelOptions" :key="g" :label="g" :value="g" />
      </el-select>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索知识点名称..."
        clearable
        size="default"
        class="!w-48"
        @keyup.enter="fetchList"
        @change="fetchList"
      />
      <span class="ml-auto text-xs text-slate-400">共 {{ points.length }} 个知识点</span>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="points.length === 0" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">📚</div>
      <div class="text-sm">还没有知识点，点击右上角添加</div>
    </div>

    <div v-else class="space-y-5">
      <div v-for="(subjects, grade) in grouped()" :key="grade" class="card p-5">
        <h3 class="font-semibold text-slate-700 mb-3">{{ grade }}</h3>
        <div v-for="(items, subject) in subjects" :key="subject" class="mb-3 last:mb-0">
          <div class="text-xs font-medium mb-2 flex items-center gap-1.5" :class="subjectTextClass(subject)">
            <span class="w-1.5 h-1.5 rounded-full bg-current"></span>{{ subject }}
          </div>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="p in items"
              :key="p.id"
              class="group inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border transition hover:shadow-sm"
              :class="subjectChipClass(p.subject)"
            >
              <div>
                <div class="text-sm font-medium">{{ p.name }}</div>
                <div v-if="p.category || p.description" class="text-[10px] text-slate-400 mt-0.5">
                  <span v-if="p.category">{{ p.category }}</span>
                  <span v-if="p.category && p.description"> · </span>
                  <span v-if="p.description">{{ p.description }}</span>
                </div>
              </div>
              <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                <button class="text-xs text-brand-600 hover:text-brand-700" @click="openEdit(p)">编辑</button>
                <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(p)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑知识点' : '添加知识点'" width="480px">
      <el-form label-position="top">
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="科目" required>
            <el-select v-model="form.subject" filterable allow-create class="w-full">
              <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
            </el-select>
          </el-form-item>
          <el-form-item label="知识点名称" required>
            <el-input v-model="form.name" placeholder="如：一元一次方程" maxlength="128" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="form.category" placeholder="如：代数 / 几何" maxlength="64" />
          </el-form-item>
          <el-form-item label="年级">
            <el-input v-model="form.grade_level" placeholder="如：三年级 / 初二" maxlength="32" />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选补充说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>
  </div>
</template>
