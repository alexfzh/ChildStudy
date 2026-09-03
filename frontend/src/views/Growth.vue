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

// ---------- 标准对照 (按月龄) ----------
function lookupStdRow(metric, gender, months) {
  // 0-83 月走 height_0_83_months, 7-18 岁走 height_7_18_years
  if (!standards.value || months == null) return null;
  const g = (gender || "male").toLowerCase();
  if (months <= 83) {
    const table = standards.value[metric === "height" ? "height_0_83_months" : "weight_0_83_months"];
    return table?.[g]?.[String(months)] || null;
  } else {
    const yr = months / 12;
    const table = standards.value[metric === "height" ? "height_7_18_years" : "weight_7_18_years"];
    // 找最接近的整岁
    if (!table?.[g]) return null;
    const years = Object.keys(table[g]).map(Number).sort((a, b) => a - b);
    const nearest = years.reduce((prev, curr) => Math.abs(curr - yr) < Math.abs(prev - yr) ? curr : prev);
    return table[g][nearest] || null;
  }
}

function heightStdRow(ageMonths) {
  return lookupStdRow("height", childStore.current?.gender, ageMonths);
}

function weightStdRow(ageMonths) {
  return lookupStdRow("weight", childStore.current?.gender, ageMonths);
}

const heightStandard = computed(() => {
  const am = ageMonths.value;
  if (am == null) return null;
  const row = heightStdRow(am);
  if (!row) return null;
  // height_0_83_months 是 [P3, P15, P50, P85, P97] 五档, height_7_18_years 是 [P3, P50, P97] 三档
  return row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] };
});

const weightStandard = computed(() => {
  const am = ageMonths.value;
  if (am == null) return null;
  const row = weightStdRow(am);
  if (!row) return null;
  return row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] };
});

function ageDisplay(months) {
  if (months == null) return "-";
  const yr = Math.floor(months / 12);
  const mo = months % 12;
  if (yr === 0) return `${mo} 月`;
  if (mo === 0) return `${yr} 岁`;
  return `${yr} 岁 ${mo} 月`;
}

function categoryByRange(value, std) {
  if (!std || value == null) return { label: "-", color: "default" };
  // 7-18 岁 只有 P3/P50/P97 三档
  const hasFive = std.p15 != null;
  const p3 = std.p3;
  const p97 = std.p97;
  const p50 = std.p50;
  if (value < p3) return { label: "下（<P3）", color: "info" };
  if (hasFive && value < std.p15) return { label: "中下", color: "slate" };
  if (value < p50) return { label: "中下", color: "slate" };
  if (value <= p50) return { label: "中位数", color: "success" };
  if (hasFive && value <= std.p85) return { label: "中上", color: "success" };
  if (value <= p97) return { label: "中上", color: "success" };
  return { label: "上（≥P97）", color: "warning" };
}

const heightVsStd = computed(() => {
  if (!latestHeight.value || !heightStandard.value) return null;
  return categoryByRange(latestHeight.value, heightStandard.value);
});

const weightVsStd = computed(() => {
  if (!latestWeight.value || !weightStandard.value) return null;
  return categoryByRange(latestWeight.value, weightStandard.value);
});

// ---------- 整岁对照表 ----------
const yearlyStandards = computed(() => {
  if (!standards.value) return [];
  const g = (childStore.current?.gender || "male").toLowerCase();
  const out = [];
  // 0-7 岁 (整月龄: 0/12/24/36/48/60/72/84)
  const h0 = standards.value.height_0_83_months?.[g] || {};
  const w0 = standards.value.weight_0_83_months?.[g] || {};
  const infantMonths = [0, 12, 24, 36, 48, 60, 72, 84];
  for (const m of infantMonths) {
    if (h0[m]) {
      out.push({
        label: m === 0 ? "出生" : `${m / 12} 岁`,
        months: m,
        height: h0[m],
        weight: w0[m],
        source: "WS/T 423",
      });
    }
  }
  // 7-18 岁 (整岁)
  const h7 = standards.value.height_7_18_years?.[g] || {};
  const w7 = standards.value.weight_7_18_years?.[g] || {};
  for (let y = 7; y <= 18; y++) {
    if (h7[y]) {
      out.push({
        label: `${y} 岁`,
        months: y * 12,
        height: h7[y], // [P3, P50, P97]
        weight: w7[y],
        source: "WS/T 611",
      });
    }
  }
  return out;
});

const currentMonthIndex = computed(() => {
  const am = ageMonths.value;
  if (am == null) return -1;
  return yearlyStandards.value.findIndex((r) => r.months === am);
});

// 点表格中任意行 → 设 pickedAge → 卡片显示该年龄的标准值
const pickedAge = ref(null);
const pickedAgeLabel = computed(() => {
  if (pickedAge.value == null) return null;
  return ageDisplay(pickedAge.value);
});
const pickedHeightStd = computed(() => {
  if (pickedAge.value == null) return null;
  const row = heightStdRow(pickedAge.value);
  return row ? (row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] }) : null;
});
const pickedWeightStd = computed(() => {
  if (pickedAge.value == null) return null;
  const row = weightStdRow(pickedAge.value);
  return row ? (row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] }) : null;
});
function onPickAge(months) {
  pickedAge.value = months;
}
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
        <div v-if="heightStandard && latestHeight" class="mt-2 pt-2 border-t border-slate-100">
          <div class="text-xs text-slate-400">本年龄标准</div>
          <div class="text-xs text-slate-600 mt-1">
            P3 <span class="font-mono">{{ heightStandard.p3 }}</span> · P50 <span class="font-mono">{{ heightStandard.p50 }}</span> · P97 <span class="font-mono">{{ heightStandard.p97 }}</span>
          </div>
          <div v-if="heightVsStd" class="mt-1">
            <span class="text-xs px-2 py-0.5 rounded-full" :class="{
              'bg-sky-50 text-sky-600': heightVsStd.color === 'info',
              'bg-slate-100 text-slate-700': heightVsStd.color === 'slate',
              'bg-emerald-50 text-emerald-700': heightVsStd.color === 'success',
              'bg-amber-50 text-amber-700': heightVsStd.color === 'warning',
            }">{{ heightVsStd.label }}</span>
          </div>
        </div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">最新体重</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ latestWeight ? latestWeight + ' kg' : '-' }}</div>
        <div v-if="weightStandard && latestWeight" class="mt-2 pt-2 border-t border-slate-100">
          <div class="text-xs text-slate-400">本年龄标准</div>
          <div class="text-xs text-slate-600 mt-1">
            P3 <span class="font-mono">{{ weightStandard.p3 }}</span> · P50 <span class="font-mono">{{ weightStandard.p50 }}</span> · P97 <span class="font-mono">{{ weightStandard.p97 }}</span>
          </div>
          <div v-if="weightVsStd" class="mt-1">
            <span class="text-xs px-2 py-0.5 rounded-full" :class="{
              'bg-sky-50 text-sky-600': weightVsStd.color === 'info',
              'bg-slate-100 text-slate-700': weightVsStd.color === 'slate',
              'bg-emerald-50 text-emerald-700': weightVsStd.color === 'success',
              'bg-amber-50 text-amber-700': weightVsStd.color === 'warning',
            }">{{ weightVsStd.label }}</span>
          </div>
        </div>
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

    <!-- 标准查询器: 点击对照表行后显示 -->
    <div v-if="pickedAge != null" class="card p-4 mb-5 border-l-4 border-indigo-400">
      <div class="flex items-start justify-between mb-2 flex-wrap gap-2">
        <div>
          <div class="text-sm font-semibold text-slate-800">
            📍 查询：{{ pickedAgeLabel }}
            <span class="text-xs text-slate-400 ml-2">
              {{ (childStore.current?.gender || 'male') === 'male' ? '男童' : '女童' }}
            </span>
          </div>
          <div class="text-xs text-slate-500 mt-0.5">点击下方表格任意行切换</div>
        </div>
        <button class="text-xs text-slate-500 hover:text-slate-700" @click="pickedAge = null">清除 ✕</button>
      </div>
      <div v-if="pickedHeightStd || pickedWeightStd" class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
        <div v-if="pickedHeightStd" class="bg-slate-50 rounded p-3">
          <div class="text-xs text-slate-500 mb-1">身高 (cm)</div>
          <div class="grid grid-cols-5 gap-2 text-center">
            <div>
              <div class="text-xs text-slate-400">P3</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedHeightStd.p3 }}</div>
            </div>
            <div v-if="pickedHeightStd.p15 != null">
              <div class="text-xs text-slate-400">P15</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedHeightStd.p15 }}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400">P50</div>
              <div class="font-mono font-semibold text-slate-800 mt-0.5">{{ pickedHeightStd.p50 }}</div>
            </div>
            <div v-if="pickedHeightStd.p85 != null">
              <div class="text-xs text-slate-400">P85</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedHeightStd.p85 }}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400">P97</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedHeightStd.p97 }}</div>
            </div>
          </div>
        </div>
        <div v-if="pickedWeightStd" class="bg-slate-50 rounded p-3">
          <div class="text-xs text-slate-500 mb-1">体重 (kg)</div>
          <div class="grid grid-cols-5 gap-2 text-center">
            <div>
              <div class="text-xs text-slate-400">P3</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedWeightStd.p3 }}</div>
            </div>
            <div v-if="pickedWeightStd.p15 != null">
              <div class="text-xs text-slate-400">P15</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedWeightStd.p15 }}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400">P50</div>
              <div class="font-mono font-semibold text-slate-800 mt-0.5">{{ pickedWeightStd.p50 }}</div>
            </div>
            <div v-if="pickedWeightStd.p85 != null">
              <div class="text-xs text-slate-400">P85</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedWeightStd.p85 }}</div>
            </div>
            <div>
              <div class="text-xs text-slate-400">P97</div>
              <div class="font-mono text-slate-700 mt-0.5">{{ pickedWeightStd.p97 }}</div>
            </div>
          </div>
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

    <!-- 标准对照表 -->
    <div v-if="yearlyStandards.length" class="card p-4 mb-5">
      <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div>
          <div class="text-sm font-semibold text-slate-800">
            身高体重标准对照表
            <span class="text-xs text-slate-400 ml-2">
              {{ (childStore.current?.gender || 'male') === 'male' ? '男童' : '女童' }} · WS/T 423-2022 + WS/T 611-2018
            </span>
          </div>
          <div class="text-xs text-slate-500 mt-0.5">点击行查看其他年龄的标准参考</div>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-100">
              <th class="text-left py-2 px-3 text-slate-500 font-medium">年龄</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium" colspan="3">身高 (cm)</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium" colspan="3">体重 (kg)</th>
            </tr>
            <tr class="border-b border-slate-100">
              <th class="py-1 px-3"></th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P3</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P50</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P97</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P3</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P50</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P97</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in yearlyStandards"
              :key="row.months"
              class="border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition"
              :class="currentMonthIndex === i ? 'bg-indigo-50' : ''"
              @click="onPickAge(row.months)"
            >
              <td class="py-2 px-3 font-medium" :class="currentMonthIndex === i ? 'text-indigo-700' : 'text-slate-700'">
                {{ row.label }}
                <span v-if="currentMonthIndex === i" class="ml-1 text-xs">📍</span>
              </td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.height[0] }}</td>
              <td class="py-2 px-3 font-mono font-medium text-slate-800">
                {{ row.height[1] ?? row.height[2] }}
              </td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.height[2] }}</td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.weight[0] }}</td>
              <td class="py-2 px-3 font-mono font-medium text-slate-800">
                {{ row.weight[1] ?? row.weight[2] }}
              </td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.weight[2] }}</td>
            </tr>
          </tbody>
        </table>
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
