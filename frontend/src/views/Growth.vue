<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useChildStore } from "@/stores/child";
import { growthAPI } from "@/api";
import * as growthUtil from "@/utils/growth";

const childStore = useChildStore();
const childId = computed(() => childStore.current?.id);
const childBirthDate = computed(() => childStore.current?.birth_date);

const loading = ref(false);
const records = ref([]);
const standards = ref(null);

// ---------- BMI card ----------
const latestRecord = computed(() => records.value[0] || null);
const latestBMI = computed(() => {
  if (!latestRecord.value) return null;
  return latestRecord.value.bmi ?? growthUtil.computeBMI(latestRecord.value.height_cm, latestRecord.value.weight_kg);
});

const ageMonths = computed(() => {
  if (!latestRecord.value || !childBirthDate.value) return null;
  const bd = new Date(childBirthDate.value);
  const rd = new Date(latestRecord.value.record_date);
  return (rd.getFullYear() - bd.getFullYear()) * 12 + (rd.getMonth() - bd.getMonth());
});

const bmiAssessment = computed(() => {
  const gender = childStore.current?.gender || "male";
  return growthUtil.assessBMI(latestBMI.value, gender, ageMonths.value);
});

const bmiColorClass = computed(() => {
  const map = {
    normal: "text-emerald-600 bg-emerald-50",
    overweight: "text-amber-600 bg-amber-50",
    obese: "text-red-600 bg-red-50",
    unknown: "text-slate-400 bg-slate-50",
    approximate: "text-indigo-600 bg-indigo-50",
  };
  return map[bmiAssessment.value.category] || "text-slate-400 bg-slate-50";
});

// ---------- Charts ----------
const chartRefHeight = ref(null);
const chartRefWeight = ref(null);

function buildChartOption(seriesData, bands, title, unit) {
  return {
    title: title ? { text: title, left: "left", textStyle: { fontSize: 13, fontWeight: 600 } } : undefined,
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        if (!params || !params.length) return "";
        const p = params[0];
        const ageLabel = p.axisValue;
        let html = `<div style="font-weight:600;margin-bottom:4px">${ageLabel} 月龄</div>`;
        params.forEach((item) => {
          if (item.seriesName === "bands") return;
          html +=
            `<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin:2px 0">` +
            `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color}"></span>` +
            `<span>${item.seriesName}: <strong>${item.value[1].toFixed(1)}${unit}</strong></span>` +
            `</div>`;
        });
        return html;
      },
    },
    legend: { top: 6, icon: "circle", textStyle: { fontSize: 11 } },
    grid: { top: 50, right: 16, bottom: 30, left: 40 },
    xAxis: {
      type: "category",
      name: "月龄",
      nameLocation: "middle",
      nameGap: 24,
      axisLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: { color: "#64748b", fontSize: 11 },
      data: seriesData.map((d) => d[0]),
    },
    yAxis: {
      type: "value",
      name: unit,
      axisLine: { show: false },
      axisLabel: { color: "#64748b", fontSize: 11 },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: [
      ...bands.map((b) => ({
        name: b.name,
        type: "line",
        data: b.data,
        symbol: "none",
        lineStyle: { width: 1, type: b.lineStyle || "dashed", color: b.color || "#cbd5e1" },
        z: 0,
        silent: true,
      })),
      {
        name: "孩子",
        type: "line",
        data: seriesData,
        symbol: "circle",
        symbolSize: 7,
        lineStyle: { width: 2.5, color: "#6366f1" },
        itemStyle: { color: "#6366f1" },
        z: 2,
      },
    ],
  };
}

function renderCharts() {
  if (!standards.value || !records.value.length) return;

  const child = childStore.current;
  const gender = (child?.gender || "male").toLowerCase();
  const bd = child?.birth_date ? new Date(child.birth_date) : null;

  // Compute age in months for each record
  const points = records.value
    .map((r) => {
      if (!bd || !r.record_date) return null;
      const rd = new Date(r.record_date);
      const months = (rd.getFullYear() - bd.getFullYear()) * 12 + (rd.getMonth() - bd.getMonth());
      return { months, height: r.height_cm, weight: r.weight_kg, record: r };
    })
    .filter(Boolean)
    .sort((a, b) => a.months - b.months);

  if (!points.length) return;

  const maxMonth = Math.max(...points.map((p) => p.months), 6);

  // Build bands from standards
  function getBand(month, metric) {
    const table = standards.value[metric]?.[gender];
    if (!table) return null;
    // Find nearest month
    const keys = Object.keys(table).map(Number).sort((a, b) => a - b);
    const nearest = keys.reduce((prev, curr) => (Math.abs(curr - month) < Math.abs(prev - month) ? curr : prev));
    return table[nearest] || null;
  }

  const heightBands = [];
  const weightBands = [];
  const bandDefs = [
    { name: "P97", idx: 4, color: "#e2e8f0", lineStyle: "solid" },
    { name: "P50", idx: 2, color: "#94a3b8", lineStyle: "dashed" },
    { name: "P3", idx: 0, color: "#e2e8f0", lineStyle: "solid" },
  ];

  for (let m = 0; m <= maxMonth; m += 3) {
    const h = getBand(m, "height_0_83_months") || getBand(m, "height_7_18_years");
    const w = getBand(m, "weight_0_83_months") || getBand(m, "weight_7_18_years");
    bandDefs.forEach((b) => {
      if (h) heightBands.push([m, h[b.idx]]);
      if (w) weightBands.push([m, w[b.idx]]);
    });
  }

  // Re-group bands by name
  const groupBands = (raw, names) => {
    const result = [];
    names.forEach((name, idx) => {
      result.push({
        name,
        data: raw.filter((_, i) => i % names.length === idx),
        color: bandDefs[idx].color,
        lineStyle: bandDefs[idx].lineStyle,
      });
    });
    return result;
  };

  const hSeries = points.map((p) => [p.months, p.height]);
  const wSeries = points.map((p) => [p.months, p.weight]);

  if (chartRefHeight.value && window.echarts) {
    const hChart = window.echarts.init(chartRefHeight.value);
    hChart.setOption(
      buildChartOption(hSeries, groupBands(heightBands, ["P97", "P50", "P3"]), "身高曲线", "cm"),
      true
    );
  }
  if (chartRefWeight.value && window.echarts) {
    const wChart = window.echarts.init(chartRefWeight.value);
    wChart.setOption(
      buildChartOption(wSeries, groupBands(weightBands, ["P97", "P50", "P3"]), "体重曲线", "kg"),
      true
    );
  }
}

// ---------- Fetch ----------
async function fetchData() {
  if (!childId.value) return;
  loading.value = true;
  try {
    const [listRes, stdRes] = await Promise.all([
      growthAPI.list(childId.value),
      growthUtil.fetchStandards().catch(() => null),
    ]);
    records.value = listRes;
    standards.value = stdRes;
    if (stdRes) growthUtil.setStandards(stdRes);
    // Render charts after data + standards loaded
    setTimeout(renderCharts, 100);
  } catch (e) {
    ElMessage.error("加载生长发育数据失败");
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchData();
  window.addEventListener("resize", renderCharts);
});
watch(() => childStore.currentId, fetchData);

// ---------- CRUD ----------
const blankForm = () => ({
  record_date: new Date().toISOString().slice(0, 10),
  height_cm: "",
  weight_kg: "",
  bmi: "",
  vision_left: "",
  vision_right: "",
  note: "",
});

const dialogVisible = ref(false);
const editing = ref(null);
const form = ref(blankForm());

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
    await fetchData();
  } catch (e) { /* axios 已提示 */ }
};

const remove = async (r) => {
  await ElMessageBox.confirm(`确认删除 ${r.record_date} 的生长发育记录吗？`, "删除", { type: "warning" });
  await growthAPI.remove(r.id);
  ElMessage.success("已删除");
  await fetchData();
};

// ---------- Helpers ----------
const latestRecords = computed(() => [...records.value].slice(0, 5));
const latestHeight = computed(() => latestRecords.value[0]?.height_cm);
const latestWeight = computed(() => latestRecords.value[0]?.weight_kg);
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">生长发育</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录身高、体重、BMI，参照中国儿童生长标准</p>
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

    <!-- BMI 状态卡 -->
    <div v-if="latestRecord" class="card p-5 mb-5">
      <div class="flex items-start gap-4 flex-wrap">
        <div class="flex-1 min-w-[200px]">
          <div class="text-xs text-slate-500 mb-1">BMI 指数评估</div>
          <div class="flex items-baseline gap-3 mb-2">
            <span class="text-4xl font-bold" :class="bmiColorClass.split(' ')[0]">{{ latestBMI ?? '-' }}</span>
            <span
              class="px-3 py-1 rounded-full text-sm font-medium"
              :class="bmiColorClass"
            >
              {{ bmiAssessment.label }}
            </span>
          </div>
          <div class="text-xs text-slate-500">
            适用标准：{{ bmiAssessment.source }}
          </div>
          <div v-if="bmiAssessment.cutoff" class="text-xs text-slate-400 mt-1">
            超重 ≥ {{ bmiAssessment.cutoff[0] }}，肥胖 ≥ {{ bmiAssessment.cutoff[1] }}（单位：kg/m²）
          </div>
        </div>
        <div class="text-xs text-slate-400 max-w-xs">
          <strong class="text-slate-600">说明：</strong>
          <span v-if="ageMonths <= 83">0-7 岁采用《7 岁以下儿童生长标准》（WS/T 423-2022）百分位法。P3-P97 为正常范围。</span>
          <span v-else>6-18 岁采用《学龄儿童青少年超重与肥胖筛查》（WS/T 586-2018）性别年龄别 BMI 切点。</span>
        </div>
      </div>
    </div>

    <!-- 曲线图 -->
    <div v-if="records.length" class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
      <div class="card p-4">
        <div ref="chartRefHeight" style="width:100%;height:320px;"></div>
      </div>
      <div class="card p-4">
        <div ref="chartRefWeight" style="width:100%;height:320px;"></div>
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
