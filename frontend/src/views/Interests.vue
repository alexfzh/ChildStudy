<script setup>
import { ref, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { interestsAPI } from "@/api";

const childStore = useChildStore();
const childId = computed(() => childStore.current?.id);

const loading = ref(false);
const records = ref([]);

const dialogVisible = ref(false);
const editing = ref(null);

const activityTypeOptions = ["运动", "音乐", "美术", "编程", "阅读", "其他"];
const skillLevelMap = { beginner: "入门", intermediate: "进阶", advanced: "精通" };

const blankForm = () => ({
  record_date: new Date().toISOString().slice(0, 10),
  activity_type: "运动",
  activity_name: "",
  duration_minutes: "",
  skill_level: "beginner",
  note: "",
});

const form = ref(blankForm());

const fetchList = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    records.value = await interestsAPI.list(childId.value);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchList);

const openCreate = () => {
  editing.value = null;
  form.value = blankForm();
  dialogVisible.value = true;
};

const openEdit = (r) => {
  editing.value = r;
  form.value = {
    record_date: r.record_date,
    activity_type: r.activity_type,
    activity_name: r.activity_name,
    duration_minutes: r.duration_minutes ?? "",
    skill_level: r.skill_level,
    note: r.note ?? "",
  };
  dialogVisible.value = true;
};

const submit = async () => {
  const data = {
    ...form.value,
    duration_minutes: form.value.duration_minutes ? Number(form.value.duration_minutes) : null,
  };
  try {
    if (editing.value) {
      await interestsAPI.update(editing.value.id, data);
      ElMessage.success("已更新");
    } else {
      await interestsAPI.create(childId.value, data);
      ElMessage.success("已添加");
    }
    dialogVisible.value = false;
    await fetchList();
  } catch (e) { /* axios 已提示 */ }
};

const remove = async (r) => {
  await ElMessageBox.confirm(`确认删除「${r.activity_name}」吗？`, "删除", { type: "warning" });
  await interestsAPI.remove(r.id);
  ElMessage.success("已删除");
  await fetchList();
};

// 按活动类型分组
const grouped = computed(() => {
  const map = {};
  records.value.forEach((r) => {
    const t = r.activity_type || "其他";
    if (!map[t]) map[t] = [];
    map[t].push(r);
  });
  return map;
});

const typeColors = {
  "运动": "bg-emerald-50 text-emerald-700 border-emerald-200",
  "音乐": "bg-purple-50 text-purple-700 border-purple-200",
  "美术": "bg-pink-50 text-pink-700 border-pink-200",
  "编程": "bg-blue-50 text-blue-700 border-blue-200",
  "阅读": "bg-amber-50 text-amber-700 border-amber-200",
  "其他": "bg-slate-50 text-slate-600 border-slate-200",
};
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">兴趣特长</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录课外活动、才艺、运动项目</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 添加记录</button>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="!records.length" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">🎨</div>
      <div class="text-sm">还没有记录，点击右上角添加</div>
    </div>

    <div v-else class="space-y-4">
      <div v-for="(items, type) in grouped()" :key="type" class="card p-5">
        <div class="flex items-center gap-2 mb-3">
          <span class="px-2.5 py-1 rounded-lg text-xs font-medium border" :class="typeColors[type] || typeColors['其他']">{{ type }}</span>
          <span class="text-xs text-slate-400">{{ items.length }} 条记录</span>
        </div>
        <div class="space-y-2">
          <div v-for="r in items" :key="r.id" class="flex items-center justify-between p-3 rounded-lg bg-slate-50/60 hover:bg-slate-50">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-slate-700">{{ r.activity_name }}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-50 text-brand-600">{{ skillLevelMap[r.skill_level] || r.skill_level }}</span>
              </div>
              <div class="text-xs text-slate-400 mt-0.5">
                {{ r.record_date }}
                <span v-if="r.duration_minutes"> · {{ r.duration_minutes }} 分钟</span>
              </div>
              <div v-if="r.note" class="text-xs text-slate-400 mt-0.5">{{ r.note }}</div>
            </div>
            <div class="flex gap-1 flex-shrink-0 ml-3">
              <button class="text-xs text-brand-600 hover:text-brand-700" @click="openEdit(r)">编辑</button>
              <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(r)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑记录' : '添加记录'" width="460px">
      <el-form label-position="top">
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="日期" required>
            <el-input v-model="form.record_date" type="date" />
          </el-form-item>
          <el-form-item label="活动类型" required>
            <el-select v-model="form.activity_type" class="w-full">
              <el-option v-for="t in activityTypeOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="活动名称" required>
            <el-input v-model="form.activity_name" placeholder="如：游泳、钢琴、足球" maxlength="128" />
          </el-form-item>
          <el-form-item label="时长 (分钟)">
            <el-input v-model="form.duration_minutes" type="number" />
          </el-form-item>
          <el-form-item label="技能水平">
            <el-select v-model="form.skill_level" class="w-full">
              <el-option label="入门" value="beginner" />
              <el-option label="进阶" value="intermediate" />
              <el-option label="精通" value="advanced" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注" class="col-span-2">
            <el-input v-model="form.note" type="textarea" :rows="2" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>
  </div>
</template>
