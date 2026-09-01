<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { growthAPI } from "@/api";

const childStore = useChildStore();
const childId = computed(() => childStore.current?.id);

const loading = ref(false);
const records = ref([]);

const dialogVisible = ref(false);
const editing = ref(null);

const blankForm = () => ({
  record_date: new Date().toISOString().slice(0, 10),
  height_cm: "",
  weight_kg: "",
  bmi: "",
  vision_left: "",
  vision_right: "",
  note: "",
});

const form = ref(blankForm());

const fetchList = async () => {
  if (!childId.value) return;
  loading.value = true;
  try {
    records.value = await growthAPI.list(childId.value);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchList);
watch(() => childStore.currentId, fetchList);

const openCreate = () => {
  editing.value = null;
  form.value = blankForm();
  dialogVisible.value = true;
};

const openEdit = (r) => {
  editing.value = r;
  form.value = {
    record_date: r.record_date,
    height_cm: r.height_cm ?? "",
    weight_kg: r.weight_kg ?? "",
    bmi: r.bmi ?? "",
    vision_left: r.vision_left ?? "",
    vision_right: r.vision_right ?? "",
    note: r.note ?? "",
  };
  dialogVisible.value = true;
};

const submit = async () => {
  const data = {
    ...form.value,
    height_cm: form.value.height_cm ? Number(form.value.height_cm) : null,
    weight_kg: form.value.weight_kg ? Number(form.value.weight_kg) : null,
    bmi: form.value.bmi ? Number(form.value.bmi) : null,
    vision_left: form.value.vision_left ? Number(form.value.vision_left) : null,
    vision_right: form.value.vision_right ? Number(form.value.vision_right) : null,
  };
  try {
    if (editing.value) {
      await growthAPI.update(editing.value.id, data);
      ElMessage.success("已更新");
    } else {
      await growthAPI.create(childId.value, data);
      ElMessage.success("已添加");
    }
    dialogVisible.value = false;
    await fetchList();
  } catch (e) { /* axios 已提示 */ }
};

const remove = async (r) => {
  await ElMessageBox.confirm(`确认删除 ${r.record_date} 的生长发育记录吗？`, "删除", { type: "warning" });
  await growthAPI.remove(r.id);
  ElMessage.success("已删除");
  await fetchList();
};

// 最近 5 条身高体重预览
const latestRecords = computed(() => [...records.value].slice(0, 5));
const latestHeight = computed(() => latestRecords.value[0]?.height_cm);
const latestWeight = computed(() => latestRecords.value[0]?.weight_kg);
const latestBMI = computed(() => latestRecords.value[0]?.bmi);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">生长发育</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录身高、体重、BMI、视力变化</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 添加记录</button>
    </div>

    <!-- 最新数据卡片 -->
    <div v-if="records.length" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      <div class="card p-4">
        <div class="text-xs text-slate-500">最新身高</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ latestHeight ? latestHeight + ' cm' : '-' }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">最新体重</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ latestWeight ? latestWeight + ' kg' : '-' }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">BMI</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ latestBMI ?? '-' }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">记录次数</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ records.length }} 次</div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="!records.length" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">📏</div>
      <div class="text-sm">还没有记录，点击右上角添加</div>
    </div>

    <div v-else class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="text-left py-3 px-4 text-slate-500 font-medium">日期</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">身高 (cm)</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">体重 (kg)</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">BMI</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">左眼视力</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">右眼视力</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">备注</th>
            <th class="text-right py-3 px-4 text-slate-500 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-3 px-4">{{ r.record_date }}</td>
            <td class="py-3 px-4">{{ r.height_cm ?? '-' }}</td>
            <td class="py-3 px-4">{{ r.weight_kg ?? '-' }}</td>
            <td class="py-3 px-4">{{ r.bmi ?? '-' }}</td>
            <td class="py-3 px-4">{{ r.vision_left ?? '-' }}</td>
            <td class="py-3 px-4">{{ r.vision_right ?? '-' }}</td>
            <td class="py-3 px-4 text-slate-400 max-w-[200px] truncate">{{ r.note || '-' }}</td>
            <td class="py-3 px-4 text-right">
              <button class="text-xs text-brand-600 hover:text-brand-700 mr-2" @click="openEdit(r)">编辑</button>
              <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑记录' : '添加记录'" width="460px">
      <el-form label-position="top">
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="日期" required>
            <el-input v-model="form.record_date" type="date" />
          </el-form-item>
          <el-form-item label="身高 (cm)">
            <el-input v-model="form.height_cm" type="number" step="0.1" />
          </el-form-item>
          <el-form-item label="体重 (kg)">
            <el-input v-model="form.weight_kg" type="number" step="0.1" />
          </el-form-item>
          <el-form-item label="BMI">
            <el-input v-model="form.bmi" type="number" step="0.1" />
          </el-form-item>
          <el-form-item label="左眼视力">
            <el-input v-model="form.vision_left" type="number" step="0.1" />
          </el-form-item>
          <el-form-item label="右眼视力">
            <el-input v-model="form.vision_right" type="number" step="0.1" />
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
