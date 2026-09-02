<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";
import { useChildStore } from "@/stores/child";
import { useAuthStore } from "@/stores/auth";
import { timelineAPI } from "@/api";

const childStore = useChildStore();
const auth = useAuthStore();
const readOnly = computed(() => auth.isChild); // 孩子账号只能查看

const loading = ref(false);
const events = ref([]);
const filterType = ref("");
const keyword = ref("");

const blank = () => ({
  child_id: childStore.currentId,
  event_type: "milestone",
  title: "",
  description: "",
  event_date: dayjs().format("YYYY-MM-DD"),
  tags: [],
  attachments: [],
});

const form = ref(blank());
const dialogVisible = ref(false);
const editing = ref(null);

// 附件上传
const fileInputRef = ref(null);

const readFilesAsBase64 = async (files) => {
  const toBase64 = (file) =>
    new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.readAsDataURL(file);
    });
  return Promise.all(Array.from(files).map(toBase64));
};

const onFilesSelected = async (e) => {
  const bases = await readFilesAsBase64(e.target.files);
  form.value.attachments = [...(form.value.attachments || []), ...bases];
  if (fileInputRef.value) fileInputRef.value.value = "";
};

const removeAttachment = (idx) => {
  form.value.attachments.splice(idx, 1);
};

const fetchList = async () => {
  if (!childStore.currentId) return;
  loading.value = true;
  try {
    events.value = await timelineAPI.list({
      child_id: childStore.currentId,
      event_type: filterType.value || undefined,
      keyword: keyword.value.trim() || undefined,
    });
  } finally {
    loading.value = false;
  }
};

onMounted(fetchList);
watch(() => childStore.currentId, fetchList);
watch(filterType, fetchList);
watch(keyword, fetchList);

const openCreate = () => {
  editing.value = null;
  form.value = blank();
  dialogVisible.value = true;
};
const openEdit = (e) => {
  editing.value = e;
  form.value = { ...blank(), ...e, tags: [...(e.tags || [])] };
  dialogVisible.value = true;
};

const submit = async () => {
  if (!form.value.title) {
    ElMessage.warning("请填写事件标题");
    return;
  }
  if (editing.value) {
    await timelineAPI.update(editing.value.id, form.value);
    ElMessage.success("已更新");
  } else {
    await timelineAPI.create(form.value);
    ElMessage.success("已添加");
  }
  dialogVisible.value = false;
  await fetchList();
};

const remove = async (e) => {
  await ElMessageBox.confirm(`确认删除「${e.title}」吗？`, "删除", { type: "warning" });
  await timelineAPI.remove(e.id);
  ElMessage.success("已删除");
  await fetchList();
};

const typeMeta = (t) => ({
  exam: { label: "考试", color: "bg-brand-100 text-brand-700", icon: "📝" },
  award: { label: "荣誉", color: "bg-amber-100 text-amber-700", icon: "🏆" },
  milestone: { label: "里程碑", color: "bg-emerald-100 text-emerald-700", icon: "🌟" },
  note: { label: "日常", color: "bg-slate-100 text-slate-600", icon: "📌" },
})[t] || { label: t, color: "bg-slate-100 text-slate-600", icon: "📌" };

// 按年月分组
const grouped = () => {
  const groups = {};
  events.value.forEach((e) => {
    const key = dayjs(e.event_date).format("YYYY 年 MM 月");
    if (!groups[key]) groups[key] = [];
    groups[key].push(e);
  });
  return groups;
};
</script>

<template>
  <div v-if="!childStore.currentId" class="card p-10 text-center text-slate-500">
    请先在「孩子档案」中添加孩子
  </div>

  <div v-else>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">成长时间轴</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录学习旅程中的重要时刻</p>
      </div>
      <button v-if="!readOnly" class="btn-primary" @click="openCreate">+ 记录事件</button>
      <span v-else class="text-xs text-slate-400 bg-slate-50 border border-slate-200 px-3 py-1 rounded-full">
        👀 只读模式
      </span>
    </div>

    <div class="card p-3 mb-4 flex gap-2 flex-wrap items-center">
      <el-radio-group v-model="filterType" size="small">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="milestone">里程碑</el-radio-button>
        <el-radio-button value="award">荣誉</el-radio-button>
        <el-radio-button value="note">日常</el-radio-button>
      </el-radio-group>
      <el-input
        v-model="keyword"
        placeholder="搜索标题/描述/标签..."
        clearable
        size="small"
        class="!w-48 ml-auto"
        @keyup.enter="fetchList"
      />
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="events.length === 0" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">🌱</div>
      <div class="text-sm">还没有成长记录</div>
    </div>

    <div v-else class="relative pl-8">
      <!-- 时间线竖线 -->
      <div class="absolute left-3 top-2 bottom-2 w-0.5 bg-slate-200"></div>

      <div v-for="(items, month) in grouped()" :key="month" class="mb-6">
        <div class="sticky top-0 z-10 -ml-8 mb-3 pt-1">
          <span class="bg-slate-50 px-3 py-1 rounded-full text-sm font-medium text-slate-700 border border-slate-200">
            {{ month }}
          </span>
        </div>

        <div v-for="e in items" :key="e.id" class="relative mb-3 card p-4 hover:shadow-soft transition-shadow">
          <!-- 时间线节点 -->
          <div class="absolute -left-[26px] top-5 w-4 h-4 rounded-full bg-white border-2 border-brand-500 flex items-center justify-center text-[10px]">
            {{ typeMeta(e.event_type).icon }}
          </div>

          <div class="flex items-start justify-between gap-2">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-slate-800">{{ e.title }}</span>
                <span :class="['badge', typeMeta(e.event_type).color]">{{ typeMeta(e.event_type).label }}</span>
              </div>
              <div class="text-xs text-slate-400 mt-1">📅 {{ dayjs(e.event_date).format("YYYY-MM-DD") }}</div>
              <div v-if="e.description" class="text-sm text-slate-600 mt-2 leading-relaxed">{{ e.description }}</div>
              <div v-if="e.tags?.length" class="flex flex-wrap gap-1 mt-2">
                <span v-for="t in e.tags" :key="t" class="badge bg-slate-100 text-slate-600">#{{ t }}</span>
              </div>
              <div v-if="e.attachments?.length" class="flex flex-wrap gap-2 mt-3">
                <img v-for="(a, i) in e.attachments" :key="i" :src="a" class="w-16 h-16 object-cover rounded border border-slate-200" />
              </div>
            </div>
            <div v-if="!readOnly" class="flex gap-1">
              <button class="btn-ghost text-xs" @click="openEdit(e)">编辑</button>
              <button class="btn-ghost text-xs text-rose-600" @click="remove(e)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑事件' : '记录事件'" width="500px">
      <el-form label-position="top">
        <el-form-item label="类型">
          <el-select v-model="form.event_type" class="w-full">
            <el-option label="🌟 里程碑" value="milestone" />
            <el-option label="🏆 荣誉" value="award" />
            <el-option label="📌 日常记录" value="note" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="如：第一次英语演讲 / 钢琴比赛获奖" />
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="form.event_date" value-format="YYYY-MM-DD" type="date" class="w-full" />
        </el-form-item>
        <el-form-item label="详情">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="记录这个时刻的细节" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tagsText" placeholder="逗号分隔，如：阅读, 演讲" @input="form.tags = $event.split(/[,，]/).map(s => s.trim()).filter(Boolean)" />
          <div class="flex flex-wrap gap-1 mt-2">
            <span v-for="t in form.tags" :key="t" class="badge bg-slate-100 text-slate-600">#{{ t }}</span>
          </div>
        </el-form-item>
        <el-form-item label="附件">
          <input ref="fileInputRef" type="file" multiple accept="image/*" class="block text-sm" @change="onFilesSelected" />
          <div v-if="form.attachments?.length" class="flex flex-wrap gap-2 mt-2">
            <div v-for="(a, i) in form.attachments" :key="i" class="relative w-16 h-16">
              <img :src="a" class="w-16 h-16 object-cover rounded border border-slate-200" />
              <button type="button" class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-rose-500 text-white text-[10px] leading-4 text-center" @click.prevent="removeAttachment(i)">×</button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>
  </div>
</template>
