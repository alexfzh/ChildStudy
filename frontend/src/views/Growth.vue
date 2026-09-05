<script setup>
import { ref, computed, onMounted, watch, nextTick } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useChildStore } from "@/stores/child"
import { growthAPI } from "@/api"
import * as growthUtil from "@/utils/growth"
// ECharts 模块化导入（与 BaseChart.vue 一致，不依赖 window.echarts）
import * as echarts from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { LineChart } from "echarts/charts"
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from "echarts/components"

echarts.use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent])

const childStore = useChildStore()
const childId = computed(() => childStore.current?.id)
const childBirthDate = computed(() => childStore.current?.birth_date)
const childGender = computed(() => (childStore.current?.gender || "male").toLowerCase())

const loading = ref(false)
const records = ref([])
const standards = ref(null)

// ---------- 最新数据 ----------
const latestRecord = computed(() => records.value[0] || null)
const latestHeight = computed(() => latestRecord.value?.height_cm ?? null)
const latestWeight = computed(() => latestRecord.value?.weight_kg ?? null)
const latestBMI = computed(() => {
  if (!latestRecord.value) return null
  return latestRecord.value.bmi ?? growthUtil.computeBMI(latestRecord.value.height_cm, latestRecord.value.weight_kg)
})

const ageMonths = computed(() => {
  if (!latestRecord.value || !childBirthDate.value) return null
  const bd = new Date(childBirthDate.value)
  const rd = new Date(latestRecord.value.record_date)
  return (rd.getFullYear() - bd.getFullYear()) * 12 + (rd.getMonth() - bd.getMonth())
})

const bmiAssessment = computed(() => growthUtil.assessBMI(latestBMI.value, childGender.value, ageMonths.value))
const bmiColorClass = computed(() => {
  const map = {
    normal: "text-emerald-600 bg-emerald-50",
    overweight: "text-amber-600 bg-amber-50",
    obese: "text-red-600 bg-red-50",
    unknown: "text-slate-400 bg-slate-50",
    approximate: "text-indigo-600 bg-indigo-50",
    thin: "text-sky-600 bg-sky-50",
    severe_thin: "text-rose-600 bg-rose-50",
  }
  return map[bmiAssessment.value.category] || "text-slate-400 bg-slate-50"
})

// BMI 身体状态说明（儿童口径：阈值随年龄/性别由标准表自动判定，非成人固定数值）
const bmiAdvice = {
  severe_thin: {
    title: "中重度消瘦",
    tone: "text-rose-700",
    bg: "bg-rose-50 border-rose-200",
    desc: "BMI 已低于中重度消瘦界，属于营养不良筛查阳性，需高度重视。",
    advice: "建议尽早就诊儿科 / 营养科，排查疾病与膳食摄入问题，在专业指导下制定营养干预方案。",
  },
  thin: {
    title: "偏瘦",
    tone: "text-sky-700",
    bg: "bg-sky-50 border-sky-200",
    desc: "BMI 低于同龄同性别参考下限，可能存在营养摄入不足或消耗偏大。",
    advice: "建议保证均衡饮食与足量优质蛋白、能量摄入，规律进餐；如持续偏低，可咨询儿科或营养科评估。",
  },
  normal: {
    title: "正常",
    tone: "text-emerald-700",
    bg: "bg-emerald-50 border-emerald-200",
    desc: "体型处于同龄同性别正常范围，健康风险较低。",
    advice: "保持均衡饮食、规律作息与适量户外运动即可。",
  },
  overweight: {
    title: "超重",
    tone: "text-amber-700",
    bg: "bg-amber-50 border-amber-200",
    desc: "BMI 已达超重界，需关注代谢异常等健康风险。",
    advice: "控制高热量零食与含糖饮料，增加运动、减少久坐，保持规律作息，动态监测变化。",
  },
  obese: {
    title: "肥胖",
    tone: "text-red-700",
    bg: "bg-red-50 border-red-200",
    desc: "BMI 已达肥胖界，与心血管、代谢性疾病风险密切相关。",
    advice: "建议尽早到儿科 / 内分泌科 / 营养门诊评估，在医生指导下调整饮食结构与增加运动。",
  },
}

// 当前最新记录对应的 BMI 身体状态说明（若无明确评估则不显示卡）
const currentBmiInfo = computed(() => {
  const cat = bmiAssessment.value?.category
  if (!cat || !bmiAdvice[cat]) return null
  return {
    category: cat,
    advice: bmiAdvice[cat],
    assessment: bmiAssessment.value,
  }
})

// ---------- 标准 lookup ----------
function lookupStdRow(metric, months) {
  if (!standards.value || months == null) return null
  const g = childGender.value
  if (months <= 83) {
    const table = standards.value[metric === "height" ? "height_0_83_months" : "weight_0_83_months"]
    return table?.[g]?.[String(months)] || null
  } else {
    const yr = months / 12
    const table = standards.value[metric === "height" ? "height_7_18_years" : "weight_7_18_years"]
    if (!table?.[g]) return null
    const years = Object.keys(table[g])
      .map(Number)
      .sort((a, b) => a - b)
    const nearest = years.reduce((prev, curr) => (Math.abs(curr - yr) < Math.abs(prev - yr) ? curr : prev))
    return table[g][nearest] || null
  }
}

function heightStdRow(months) {
  const row = lookupStdRow("height", months)
  if (!row) return null
  return row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] }
}

function weightStdRow(months) {
  const row = lookupStdRow("weight", months)
  if (!row) return null
  return row.length >= 5
    ? { p3: row[0], p15: row[1], p50: row[2], p85: row[3], p97: row[4] }
    : { p3: row[0], p50: row[1], p97: row[2] }
}

function categoryByRange(value, std) {
  if (!std || value == null) return { label: "-", color: "default" }
  const hasFive = std.p15 != null
  const { p3, p50, p97 } = std
  if (value < p3) return { label: "下（<P3）", color: "info" }
  if (hasFive) {
    // 5 档：P3 / P15 / P50 / P85 / P97
    if (value <= std.p15) return { label: "中下", color: "slate" }
    if (value <= std.p85) return { label: "中", color: "success" }
    if (value <= p97) return { label: "中上", color: "success" }
  } else {
    // 3 档兼容（旧数据 / 7-18 岁体重非国标）：P3 / P50 / P97
    if (value <= p50) return { label: "中下", color: "slate" }
    if (value <= p97) return { label: "中上", color: "success" }
  }
  return { label: "上（≥P97）", color: "warning" }
}

function ageDisplay(months) {
  if (months == null) return "-"
  const yr = Math.floor(months / 12)
  const mo = months % 12
  if (yr === 0) return `${mo} 月`
  if (mo === 0) return `${yr} 岁`
  return `${yr} 岁 ${mo} 月`
}

// ---------- 最新记录的标准值（用于顶部卡片） ----------
const heightStandard = computed(() => {
  const am = ageMonths.value
  if (am == null) return null
  return heightStdRow(am)
})

const weightStandard = computed(() => {
  const am = ageMonths.value
  if (am == null) return null
  return weightStdRow(am)
})

const heightVsStd = computed(() => {
  if (!latestHeight.value || !heightStandard.value) return null
  return categoryByRange(latestHeight.value, heightStandard.value)
})

const weightVsStd = computed(() => {
  if (!latestWeight.value || !weightStandard.value) return null
  return categoryByRange(latestWeight.value, weightStandard.value)
})

// ---------- 详细对比总表（核心） ----------
const enrichedRecords = computed(() => {
  if (!records.value.length || !standards.value) return records.value
  const bd = childBirthDate.value ? new Date(childBirthDate.value) : null
  const g = childGender.value
  return records.value
    .map((r) => {
      const rd = new Date(r.record_date)
      const months = bd ? (rd.getFullYear() - bd.getFullYear()) * 12 + (rd.getMonth() - bd.getMonth()) : null
      const hStd = heightStdRow(months)
      const wStd = weightStdRow(months)
      const bmi = r.bmi ?? growthUtil.computeBMI(r.height_cm, r.weight_kg)
      const bmiAssess = growthUtil.assessBMI(bmi, g, months)
      const hCat = hStd ? categoryByRange(r.height_cm, hStd) : null
      const wCat = wStd ? categoryByRange(r.weight_kg, wStd) : null
      return {
        ...r,
        ageMonths: months,
        ageLabel: ageDisplay(months),
        heightStd: hStd,
        weightStd: wStd,
        bmi,
        bmiAssessment: bmiAssess,
        heightCategory: hCat,
        weightCategory: wCat,
      }
    })
    .sort((a, b) => {
      const am = (b.ageMonths ?? 0) - (a.ageMonths ?? 0)
      if (am !== 0) return am
      return new Date(b.record_date) - new Date(a.record_date)
    })
})

// ---------- 整岁对照表 ----------
// 2026-09-05：身高升级 5 档 (P3/P15/P50/P85/P97) 后，
//   输出结构统一为 height/weight 对象带显式分档字段名，
//   模板按字段访问避免 [1]/[2] 这种与档数耦合的索引。
const yearlyStandards = computed(() => {
  if (!standards.value) return []
  const g = childGender.value
  const out = []
  const h0 = standards.value.height_0_83_months?.[g] || {}
  const w0 = standards.value.weight_0_83_months?.[g] || {}
  const h7 = standards.value.height_7_18_years?.[g] || {}
  const w7 = standards.value.weight_7_18_years?.[g] || {}
  const _hRow = (row) => {
    // row: [P3, P15, P50, P85, P97] 或 [P3, P50, P97]
    if (!row) return { p3: null, p15: null, p50: null, p85: null, p97: null }
    return {
      p3: row[0],
      p15: row.length >= 5 ? row[1] : null,
      p50: row.length >= 5 ? row[2] : row[1],
      p85: row.length >= 5 ? row[3] : null,
      p97: row.length >= 5 ? row[4] : row[2],
    }
  }
  const _wRow = _hRow
  const infantMonths = [0, 12, 24, 36, 48, 60, 72, 84]
  for (const m of infantMonths) {
    if (h0[m]) {
      out.push({
        label: m === 0 ? "出生" : `${m / 12} 岁`,
        months: m,
        height: _hRow(h0[m]),
        weight: _wRow(w0[m]),
        source: "WS/T 423",
        heightCols: 5, // 0-83 月身高 5 档
        weightCols: 5, // 0-83 月体重 5 档
      })
    }
  }
  for (let y = 7; y <= 18; y++) {
    if (h7[y]) {
      out.push({
        label: `${y} 岁`,
        months: y * 12,
        height: _hRow(h7[y]),
        weight: _wRow(w7[y]),
        source: "WS/T 612",
        heightCols: 5, // 7-18 岁身高 5 档（WS/T 612-2018 SD 法）
        weightCols: 3, // 7-18 岁体重 3 档（国内非国标）
      })
    }
  }
  return out
})

const currentMonthIndex = computed(() => {
  const am = ageMonths.value
  if (am == null) return -1
  return yearlyStandards.value.findIndex((r) => r.months === am)
})

// 是否有体重仅 3 档的行（7-18 岁体重沿用非国标数据）
const hasThreeColWeight = computed(() =>
  yearlyStandards.value.some((r) => r.weightCols === 3),
)

function rowHas3OnlyWeight(row) {
  return row.weightCols === 3
}

// ---------- Charts ----------
const chartRefHeight = ref(null)
const chartRefWeight = ref(null)
const chartRefBMI = ref(null)

function buildChartOption(seriesData, bands, title, unit, axisMin, axisMax) {
  return {
    title: title ? { text: title, left: "left", textStyle: { fontSize: 13, fontWeight: 600 } } : undefined,
    tooltip: {
      trigger: "axis",
      // 2026-09-05: snap 强制鼠标 x 对齐到最近数据点；体重/身高常见 1~3 个稀疏记录，
      // 不 snap 时 axisPointer 找不到最近点 → tooltip 不出。
      // triggerOn 显式开启 mousemove + click（默认 mousemove|click，但过往版本偶发失效）。
      axisPointer: {
        type: "cross",
        snap: true,
        label: { backgroundColor: "#475569" },
      },
      triggerOn: "mousemove|click",
      backgroundColor: "rgba(255,255,255,0.98)",
      borderColor: "#e2e8f0",
      textStyle: { color: "#0f172a", fontSize: 12 },
      formatter: (params) => {
        if (!params || !params.length) return ""
        const p = params[0]
        const months = p.axisValue
        const yr = Math.floor(months / 12)
        const mo = Math.round(months % 12)
        const ageLabel = yr > 0 ? `${yr} 岁 ${mo} 月` : `${mo} 月`
        let html = `<div style="font-weight:600;margin-bottom:6px;color:#0f172a">📅 ${ageLabel} (${Math.round(months)} 月龄)</div>`
        // 孩子系列优先显示；参考带后置且用浅色
        const child = params.find((it) => it.seriesName === "孩子" && it.value && it.value[1] != null)
        const refs = params.filter((it) => it.seriesName !== "孩子" && it.value && it.value[1] != null)
        if (child) {
          html +=
            `<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin:3px 0;padding:4px 6px;background:#eef2ff;border-radius:4px">` +
            `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${child.color}"></span>` +
            `<span style="font-weight:600">孩子: <strong style="color:#4338ca">${child.value[1].toFixed(1)} ${unit}</strong></span>` +
            `</div>`
        }
        if (refs.length) {
          html += `<div style="border-top:1px dashed #cbd5e1;margin:4px 0;padding-top:4px;color:#64748b;font-size:11px">参考带</div>`
          refs.forEach((item) => {
            html +=
              `<div style="display:flex;align-items:center;gap:6px;font-size:11px;margin:1px 0;color:#475569">` +
              `<span style="display:inline-block;width:8px;height:2px;background:${item.color}"></span>` +
              `<span>${item.seriesName}: <strong>${item.value[1].toFixed(1)} ${unit}</strong></span>` +
              `</div>`
          })
        }
        if (!child && !refs.length) {
          return `<div style="color:#64748b">${ageLabel} 无数据</div>`
        }
        return html
      },
    },
    legend: { show: false },
    grid: { top: 18, right: 16, bottom: 30, left: 44 },
    xAxis: {
      type: "value",
      name: "月龄",
      nameLocation: "middle",
      nameGap: 24,
      min: axisMin,
      max: axisMax,
      axisLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: { color: "#64748b", fontSize: 11, formatter: (v) => Math.round(v) },
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
        // 显式设置 itemStyle.color：图例色块取自 itemStyle，否则会回退默认调色板导致色块与线不一致
        itemStyle: { color: b.color || "#cbd5e1" },
        z: 0,
        silent: true,
      })),
      {
        name: "孩子",
        type: "line",
        data: seriesData,
        symbol: "circle",
        // 2026-09-05: 加大命中区 + emphasis hover 放大，体重/身高稀疏记录时鼠标容易命中
        symbolSize: 10,
        lineStyle: { width: 2.5, color: "#6366f1" },
        itemStyle: { color: "#6366f1" },
        emphasis: {
          focus: "series",
          scale: 1.4,
          itemStyle: { color: "#4338ca", borderColor: "#fff", borderWidth: 2 },
        },
        z: 2,
      },
    ],
  }
}

function renderCharts() {
  if (!standards.value || !records.value.length) return
  const bd = childBirthDate.value ? new Date(childBirthDate.value) : null
  const points = records.value
    .map((r) => {
      if (!bd || !r.record_date) return null
      const rd = new Date(r.record_date)
      const months = (rd.getFullYear() - bd.getFullYear()) * 12 + (rd.getMonth() - bd.getMonth())
      return {
        months,
        height: r.height_cm,
        weight: r.weight_kg,
        bmi: r.bmi ?? (r.height_cm && r.weight_kg ? growthUtil.computeBMI(r.height_cm, r.weight_kg) : null),
        record: r,
      }
    })
    .filter(Boolean)
    .sort((a, b) => a.months - b.months)

  if (!points.length) return
  const g = childGender.value
  const firstMonth = points[0].months
  const lastMonth = points[points.length - 1].months

  // X 轴取孩子记录附近窗口，避免整段 0-83 空白；带与数据都用同一 value 轴。
  const axisMin = Math.max(0, Math.floor((firstMonth - 8) / 6) * 6)
  const axisMax = lastMonth + 8

  /**
   * 取指定月龄的标准 [P3, P15, P50, P85, P97]。
   * 0-83 月走 WS/T 423-2022（月表，5 档）；
   * 84 月以上走 WS/T 612-2018（岁表，5 档 SD 法）——月龄必须 ÷12 换算成岁，
   * 不能用月龄直接匹配岁的键（旧 bug）。
   * 7-18 岁体重国内非国标，row 通常只 3 档：返回时 p15/p85 = null。
   */
  const stdTripletAt = (month) => {
    const h0 = standards.value.height_0_83_months?.[g]
    const h7 = standards.value.height_7_18_years?.[g]
    const w0 = standards.value.weight_0_83_months?.[g]
    const w7 = standards.value.weight_7_18_years?.[g]
    const rowFor = (table, want) => {
      if (!table) return null
      const keys = Object.keys(table)
        .map(Number)
        .sort((a, b) => a - b)
      if (want < keys[0] || want > keys[keys.length - 1]) return null
      const nearest = keys.reduce((p, c) => (Math.abs(c - want) < Math.abs(p - want) ? c : p))
      return table[nearest]
    }
    const pick = (r) => {
      if (!r) return null
      if (r.length >= 5) {
        return { p3: r[0], p15: r[1], p50: r[2], p85: r[3], p97: r[4] }
      }
      // 3 档（7-18 岁体重）：p15/p85 留 null
      return { p3: r[0], p15: null, p50: r[1], p85: null, p97: r[2] }
    }
    const isUnder7 = month <= 83
    return {
      height: pick(isUnder7 ? rowFor(h0, month) : rowFor(h7, month / 12)),
      weight: pick(isUnder7 ? rowFor(w0, month) : rowFor(w7, month / 12)),
    }
  }

  // 覆盖窗口内逐月生成参考带（P3/P15/P50/P85/P97 各一条；体重 7-18 岁只有 3 档）
  const heightBands = { P3: [], P15: [], P50: [], P85: [], P97: [] }
  const weightBands = { P3: [], P15: [], P50: [], P85: [], P97: [] }
  for (let m = axisMin; m <= axisMax; m++) {
    const t = stdTripletAt(m)
    if (t.height) {
      heightBands.P3.push([m, t.height.p3])
      heightBands.P15.push([m, t.height.p15])
      heightBands.P50.push([m, t.height.p50])
      heightBands.P85.push([m, t.height.p85])
      heightBands.P97.push([m, t.height.p97])
    }
    if (t.weight) {
      weightBands.P3.push([m, t.weight.p3])
      weightBands.P15.push([m, t.weight.p15])
      weightBands.P50.push([m, t.weight.p50])
      weightBands.P85.push([m, t.weight.p85])
      weightBands.P97.push([m, t.weight.p97])
    }
  }
  // 5 条参考线：低=红、次低=橙、中位=黄、次高=青绿、上=绿
  const bandStyle = {
    P3:  { color: "#ef4444", lineStyle: "dashed" },
    P15: { color: "#fb923c", lineStyle: "dashed" },
    P50: { color: "#eab308", lineStyle: "dashed" },
    P85: { color: "#06b6d4", lineStyle: "dashed" },
    P97: { color: "#22c55e", lineStyle: "dashed" },
  }
  const toBands = (map) =>
    ["P97", "P85", "P50", "P15", "P3"].map((name) => ({
      name,
      data: map[name],
      color: bandStyle[name].color,
      lineStyle: bandStyle[name].lineStyle,
    }))

  const hSeries = points.map((p) => [p.months, p.height])
  const wSeries = points.map((p) => [p.months, p.weight])

  if (chartRefHeight.value) {
    const hChart = echarts.init(chartRefHeight.value)
    hChart.setOption(buildChartOption(hSeries, toBands(heightBands), "", "cm", axisMin, axisMax), true)
  }
  if (chartRefWeight.value) {
    const wChart = echarts.init(chartRefWeight.value)
    wChart.setOption(buildChartOption(wSeries, toBands(weightBands), "", "kg", axisMin, axisMax), true)
  }

  // ---- BMI 曲线 ----
  // 参考线分两套：<7岁用 BMI_0_83 的 P3/P50/P97（WS/T 423）；≥7岁用 BMI_CUTOFFS_6_18 的
  // 超重/肥胖界值（WS/T 586）+ BMI_THIN_CUTOFFS_6_18 消瘦界（WS/T 456-2014，取轻度消瘦上限）。
  // 窗口内逐月取对应参考。
  const bmiRefAt = (month) => {
    if (month <= 83) {
      const row = standards.value.bmi_0_83_months?.[g]?.[String(month)]
      if (!row) return null
      // 0-83 月 BMI 行 5 档 [P3,P15,P50,P85,P97]
      return row.length >= 5 ? { kind: "pct", p3: row[0], p50: row[2], p97: row[4] } : null
    }
    const table = standards.value.bmi_cutoffs_6_18?.[g]
    if (!table) return null
    const keys = Object.keys(table)
      .map(Number)
      .sort((a, b) => a - b)
    if (!keys.length) return null
    const yr = month / 12
    const nearest = keys.reduce((p, c) => (Math.abs(c - yr) < Math.abs(p - yr) ? c : p))
    const row = table[String(nearest)]
    if (!row) return null
    // WS/T 456-2014: [中重度消瘦界, 轻度消瘦界]，曲线只画轻度消瘦上限（偏瘦分界）
    const thinRow = standards.value.bmi_thin_cutoffs_6_18?.[g]?.[String(nearest)]
    return { kind: "cut", ow: row[0], ob: row[1], thin: thinRow ? thinRow[1] : null }
  }
  const bmiBands = { P3: [], P50: [], P97: [], 消瘦: [], 超重: [], 肥胖: [] }
  for (let m = axisMin; m <= axisMax; m++) {
    const r = bmiRefAt(m)
    if (!r) continue
    if (r.kind === "pct") {
      bmiBands.P3.push([m, r.p3])
      bmiBands.P50.push([m, r.p50])
      bmiBands.P97.push([m, r.p97])
    } else {
      if (r.thin != null) bmiBands.消瘦.push([m, r.thin])
      bmiBands.超重.push([m, r.ow])
      bmiBands.肥胖.push([m, r.ob])
    }
  }
  const bmiStyle = {
    P3: { color: "#ef4444", ls: "dashed" },
    P50: { color: "#eab308", ls: "dashed" },
    P97: { color: "#22c55e", ls: "dashed" },
    消瘦: { color: "#0ea5e9", ls: "dashed" },
    超重: { color: "#f59e0b", ls: "dashed" },
    肥胖: { color: "#dc2626", ls: "dashed" },
  }
  const bmiBandList = ["P3", "P50", "P97", "消瘦", "超重", "肥胖"]
    .map((name) =>
      bmiBands[name].length
        ? { name, data: bmiBands[name], color: bmiStyle[name].color, lineStyle: bmiStyle[name].ls }
        : null,
    )
    .filter(Boolean)
  const bmiSeries = points.filter((p) => p.bmi != null).map((p) => [p.months, p.bmi])
  if (chartRefBMI.value && bmiSeries.length) {
    const bmiChart = echarts.init(chartRefBMI.value)
    bmiChart.setOption(buildChartOption(bmiSeries, bmiBandList, "", "kg/m²", axisMin, axisMax), true)
  }
}

// ---------- Fetch ----------
async function fetchData() {
  if (!childId.value) return
  loading.value = true
  try {
    const [listRes, stdRes] = await Promise.all([
      growthAPI.list(childId.value),
      growthUtil.fetchStandards().catch(() => null),
    ])
    records.value = listRes
    standards.value = stdRes
    if (stdRes) growthUtil.setStandards(stdRes)
    await nextTick()
    renderCharts()
  } catch (e) {
    ElMessage.error("加载生长发育数据失败")
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchData()
  window.addEventListener("resize", renderCharts)
})
watch(() => childStore.currentId, fetchData)

// ---------- CRUD ----------
const blankForm = () => ({
  record_date: new Date().toISOString().slice(0, 10),
  height_cm: "",
  weight_kg: "",
  bmi: "",
  vision_left: "",
  vision_right: "",
  note: "",
})

const dialogVisible = ref(false)
const editing = ref(null)
const form = ref(blankForm())

const openCreate = () => {
  editing.value = null
  form.value = blankForm()
  dialogVisible.value = true
}

const openEdit = (r) => {
  editing.value = r
  form.value = {
    record_date: r.record_date,
    height_cm: r.height_cm ?? "",
    weight_kg: r.weight_kg ?? "",
    bmi: r.bmi ?? "",
    vision_left: r.vision_left ?? "",
    vision_right: r.vision_right ?? "",
    // 备注 UI 已隐藏（2026-09-05），编辑时不再回填；提交时仍写空串保兼容。
    note: "",
  }
  dialogVisible.value = true
}

const submit = async () => {
  const data = {
    ...form.value,
    height_cm: form.value.height_cm ? Number(form.value.height_cm) : null,
    weight_kg: form.value.weight_kg ? Number(form.value.weight_kg) : null,
    bmi: form.value.bmi ? Number(form.value.bmi) : null,
    vision_left: form.value.vision_left ? Number(form.value.vision_left) : null,
    vision_right: form.value.vision_right ? Number(form.value.vision_right) : null,
    // 备注 UI 已隐藏（2026-09-05），提交时强制空串，不影响后端 schema。
    note: "",
  }
  try {
    if (editing.value) {
      await growthAPI.update(editing.value.id, data)
      ElMessage.success("已更新")
    } else {
      await growthAPI.create(childId.value, data)
      ElMessage.success("已添加")
    }
    dialogVisible.value = false
    await fetchData()
  } catch (e) {
    /* axios 已提示 */
  }
}

const remove = async (r) => {
  await ElMessageBox.confirm(`确认删除 ${r.record_date} 的生长发育记录吗？`, "删除", { type: "warning" })
  await growthAPI.remove(r.id)
  ElMessage.success("已删除")
  await fetchData()
}

// ---------- Helpers ----------
function stdTooltip(std, unit) {
  if (!std) return ""
  const parts = []
  if (std.p3 != null) parts.push(`P3 ${std.p3}${unit}`)
  if (std.p15 != null) parts.push(`P15 ${std.p15}${unit}`)
  if (std.p50 != null) parts.push(`P50 ${std.p50}${unit}`)
  if (std.p85 != null) parts.push(`P85 ${std.p85}${unit}`)
  if (std.p97 != null) parts.push(`P97 ${std.p97}${unit}`)
  return parts.join("\n")
}

function tagClass(color) {
  const map = {
    info: "bg-sky-50 text-sky-600",
    slate: "bg-slate-100 text-slate-700",
    success: "bg-emerald-50 text-emerald-700",
    warning: "bg-amber-50 text-amber-700",
    default: "text-slate-400",
    danger: "bg-red-50 text-red-700",
  }
  return map[color] || "text-slate-400"
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-5 flex-wrap gap-3">
      <div class="flex items-center gap-3">
        <span
          class="inline-flex items-center justify-center w-11 h-11 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white text-xl shadow-sm"
          >📈</span
        >
        <div>
          <h2 class="text-lg font-semibold text-slate-800 leading-tight">生长发育</h2>
          <p class="text-xs text-slate-500 mt-0.5">记录身高、体重、BMI，对照中国儿童生长标准（WS/T 423 · WS/T 612）</p>
        </div>
      </div>
      <button class="btn-primary" @click="openCreate">+ 添加记录</button>
    </div>

    <!-- 最新数据卡片 -->
    <!-- 最新数据卡片：每张配彩色图标与状态语义色 -->
    <div v-if="records.length" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
      <!-- 身高 -->
      <div class="card p-4 relative overflow-hidden">
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-brand-400 to-brand-600"></div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-brand-50 text-brand-600 text-base"
            >📏</span
          >
          <span class="text-xs text-slate-500">最新身高</span>
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold text-slate-800">{{ latestHeight ?? "-" }}</span>
          <span v-if="latestHeight" class="text-xs text-slate-400 font-medium">cm</span>
        </div>
        <div v-if="heightStandard && latestHeight" class="mt-2 pt-2 border-t border-slate-100">
          <div class="grid grid-cols-3 gap-x-2 gap-y-0.5">
            <div class="text-[11px] text-slate-400">P3 <span class="font-mono text-slate-500">{{ heightStandard.p3 }}</span></div>
            <div class="text-[11px] text-slate-400">P15 <span class="font-mono text-slate-500">{{ heightStandard.p15 ?? "—" }}</span></div>
            <div class="text-[11px] text-slate-400">P50 <span class="font-mono text-slate-700 font-semibold">{{ heightStandard.p50 }}</span></div>
            <div class="text-[11px] text-slate-400">P85 <span class="font-mono text-slate-500">{{ heightStandard.p85 ?? "—" }}</span></div>
            <div class="text-[11px] text-slate-400 col-span-2">P97 <span class="font-mono text-slate-500">{{ heightStandard.p97 }}</span></div>
          </div>
          <div v-if="heightVsStd" class="mt-1.5">
            <span
              class="inline-flex items-center text-[11px] px-2 py-0.5 rounded-full"
              :class="tagClass(heightVsStd.color)"
              >{{ heightVsStd.label }}</span
            >
          </div>
        </div>
      </div>
      <!-- 体重 -->
      <div class="card p-4 relative overflow-hidden">
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 to-emerald-600"></div>
        <div class="flex items-center gap-2">
          <span
            class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 text-base"
            >⚖️</span
          >
          <span class="text-xs text-slate-500">最新体重</span>
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold text-slate-800">{{ latestWeight ?? "-" }}</span>
          <span v-if="latestWeight" class="text-xs text-slate-400 font-medium">kg</span>
        </div>
        <div v-if="weightStandard && latestWeight" class="mt-2 pt-2 border-t border-slate-100">
          <div class="grid grid-cols-3 gap-x-2 gap-y-0.5">
            <div class="text-[11px] text-slate-400">P3 <span class="font-mono text-slate-500">{{ weightStandard.p3 }}</span></div>
            <div class="text-[11px] text-slate-400">P15 <span class="font-mono text-slate-500">{{ weightStandard.p15 ?? "—" }}</span></div>
            <div class="text-[11px] text-slate-400">P50 <span class="font-mono text-slate-700 font-semibold">{{ weightStandard.p50 }}</span></div>
            <div class="text-[11px] text-slate-400">P85 <span class="font-mono text-slate-500">{{ weightStandard.p85 ?? "—" }}</span></div>
            <div class="text-[11px] text-slate-400 col-span-2">P97 <span class="font-mono text-slate-500">{{ weightStandard.p97 }}</span></div>
          </div>
          <div v-if="weightVsStd" class="mt-1.5">
            <span
              class="inline-flex items-center text-[11px] px-2 py-0.5 rounded-full"
              :class="tagClass(weightVsStd.color)"
              >{{ weightVsStd.label }}</span
            >
          </div>
        </div>
      </div>
      <!-- BMI -->
      <div class="card p-4 relative overflow-hidden">
        <div class="absolute left-0 top-0 bottom-0 w-1" :class="'bg-gradient-to-b from-slate-300 to-slate-500'"></div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-xl" :class="bmiColorClass">{{
            bmiAssessment.label === "正常" ? "✅" : "🧮"
          }}</span>
          <span class="text-xs text-slate-500">BMI</span>
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold text-slate-800">{{
            latestBMI ? (latestBMI.toFixed?.(1) ?? latestBMI) : "-"
          }}</span>
          <span v-if="latestBMI" class="text-[11px] text-slate-400 font-medium">kg/m²</span>
        </div>
        <div v-if="latestBMI" class="mt-2 pt-2 border-t border-slate-100">
          <span
            v-if="bmiAssessment?.category"
            class="inline-flex items-center text-[11px] px-2 py-0.5 rounded-full"
            :class="bmiColorClass"
          >
            {{ bmiAssessment.label }}
          </span>
        </div>
      </div>
      <!-- 记录次数 / 最近记录 -->
      <div class="card p-4 relative overflow-hidden">
        <div class="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-amber-400 to-amber-600"></div>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-amber-50 text-amber-600 text-base"
            >🗓️</span
          >
          <span class="text-xs text-slate-500">记录次数</span>
        </div>
        <div class="mt-2 flex items-baseline gap-1">
          <span class="text-2xl font-bold text-slate-800">{{ records.length }}</span>
          <span class="text-xs text-slate-400 font-medium">次</span>
        </div>
        <div v-if="latestRecord" class="mt-2 pt-2 border-t border-slate-100">
          <div class="text-[11px] text-slate-400">
            最近记录 <span class="text-slate-600 font-medium">{{ latestRecord.record_date }}</span>
          </div>
          <div v-if="ageMonths != null" class="text-[11px] text-slate-400 mt-0.5">
            测量时 <span class="text-slate-600 font-medium">{{ ageDisplay(ageMonths) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 核心区域：生长发育详细对比总表 -->
    <div v-if="enrichedRecords.length" class="card mb-5 overflow-hidden">
      <div
        class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-brand-50/70 to-transparent flex items-center justify-between flex-wrap gap-2"
      >
        <div class="flex items-center gap-2">
          <span class="text-brand-600">📋</span>
          <span class="text-sm font-semibold text-slate-800">生长发育详细对比总表</span>
          <span class="hidden sm:inline text-xs text-slate-400 ml-1">
            {{ (childStore.current?.gender || "male") === "male" ? "男童" : "女童" }} · 对照中国儿童生长标准
          </span>
        </div>
      </div>
      <div class="overflow-x-auto px-2 py-2">
        <table class="w-full text-sm">
          <thead>
            <tr>
              <th class="text-left py-2 px-3 text-slate-500 font-medium bg-slate-50/60">日期</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium bg-slate-50/60">年龄</th>
              <th class="text-right py-2 px-3 text-brand-700 font-semibold bg-brand-50/40" colspan="4">📏 身高 (cm)</th>
              <th class="text-right py-2 px-3 text-emerald-700 font-semibold bg-emerald-50/40" colspan="4">
                ⚖️ 体重 (kg)
              </th>
              <th class="text-right py-2 px-3 text-slate-500 font-medium bg-slate-50/60">BMI</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium bg-slate-50/60">等级</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium bg-slate-50/60">视力</th>
              <th class="text-right py-2 px-3 text-slate-500 font-medium bg-slate-50/60">操作</th>
            </tr>
            <tr class="border-b border-slate-100">
              <th class="py-1 px-3 bg-slate-50/60"></th>
              <th class="py-1 px-3 bg-slate-50/60"></th>
              <th class="text-right py-1 px-3 text-[11px] text-brand-700 font-bold bg-brand-50/40">孩子</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-400 bg-brand-50/40">P3</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-500 font-semibold bg-brand-50/40">P50</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-400 bg-brand-50/40">P97</th>
              <th class="text-right py-1 px-3 text-[11px] text-emerald-700 font-bold bg-emerald-50/40">孩子</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-400 bg-emerald-50/40">P3</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-500 font-semibold bg-emerald-50/40">P50</th>
              <th class="text-right py-1 px-3 text-[11px] text-slate-400 bg-emerald-50/40">P97</th>
              <th class="py-1 px-3 bg-slate-50/60"></th>
              <th class="py-1 px-3 bg-slate-50/60"></th>
              <th class="py-1 px-3 bg-slate-50/60"></th>
              <th class="py-1 px-3 bg-slate-50/60"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in enrichedRecords" :key="r.id" class="border-b border-slate-50 hover:bg-brand-50/30">
              <td class="py-2 px-3 text-slate-700">{{ r.record_date }}</td>
              <td class="py-2 px-3 text-slate-500 whitespace-nowrap">{{ r.ageLabel }}</td>
              <td
                class="py-2 px-3 text-right font-mono font-bold text-brand-700"
                :title="stdTooltip(r.heightStd, 'cm')"
              >
                {{ r.height_cm ?? "-" }}
              </td>
              <td class="py-2 px-3 text-right font-mono text-slate-400">{{ r.heightStd?.p3 ?? "-" }}</td>
              <td class="py-2 px-3 text-right font-mono font-medium text-slate-600">{{ r.heightStd?.p50 ?? "-" }}</td>
              <td class="py-2 px-3 text-right font-mono text-slate-400">{{ r.heightStd?.p97 ?? "-" }}</td>
              <td
                class="py-2 px-3 text-right font-mono font-bold text-emerald-700"
                :title="stdTooltip(r.weightStd, 'kg')"
              >
                {{ r.weight_kg ?? "-" }}
              </td>
              <td class="py-2 px-3 text-right font-mono text-slate-400">{{ r.weightStd?.p3 ?? "-" }}</td>
              <td class="py-2 px-3 text-right font-mono font-medium text-slate-600">{{ r.weightStd?.p50 ?? "-" }}</td>
              <td class="py-2 px-3 text-right font-mono text-slate-400">{{ r.weightStd?.p97 ?? "-" }}</td>
              <td class="py-2 px-3 text-right font-mono text-slate-600">{{ r.bmi ?? "-" }}</td>
              <td class="py-2 px-3">
                <div class="flex flex-wrap gap-1">
                  <span
                    class="text-[11px] px-2 py-0.5 rounded-full inline-flex items-center"
                    :class="tagClass(r.heightCategory?.color)"
                  >
                    H {{ r.heightCategory?.label }}
                  </span>
                  <span
                    v-if="r.weightCategory"
                    class="text-[11px] px-2 py-0.5 rounded-full inline-flex items-center"
                    :class="tagClass(r.weightCategory?.color)"
                  >
                    W {{ r.weightCategory?.label }}
                  </span>
                  <span
                    v-if="r.bmiAssessment"
                    class="text-[11px] px-2 py-0.5 rounded-full inline-flex items-center"
                    :class="tagClass(r.bmiAssessment.color)"
                  >
                    BMI {{ r.bmiAssessment.label }}
                  </span>
                </div>
              </td>
              <td class="py-2 px-3 text-slate-500 whitespace-nowrap font-mono">
                {{ r.vision_left ?? "-" }}<span class="text-slate-300">/</span>{{ r.vision_right ?? "-" }}
              </td>
              <td class="py-2 px-3 text-right whitespace-nowrap">
                <button class="text-xs text-brand-600 hover:text-brand-700 mr-2" @click="openEdit(r)">编辑</button>
                <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(r)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 曲线图 -->
    <div v-if="records.length" class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
      <div class="card overflow-hidden">
        <div
          class="px-4 py-2 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between flex-wrap gap-2"
        >
          <span class="text-xs font-semibold text-slate-600">📏 身高曲线</span>
          <span class="flex items-center gap-2 text-[11px] text-slate-400 flex-wrap">
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-red-400"></i>P3</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-orange-400"></i>P15</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-yellow-400"></i>P50</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-cyan-500"></i>P85</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-green-400"></i>P97</span>
            <span class="inline-flex items-center gap-1"
              ><i class="w-2 h-2 inline-block rounded-full bg-indigo-500"></i>孩子</span
            >
          </span>
        </div>
        <div ref="chartRefHeight" class="p-2" style="width: 100%; height: 300px"></div>
      </div>
      <div class="card overflow-hidden">
        <div
          class="px-4 py-2 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between flex-wrap gap-2"
        >
          <span class="text-xs font-semibold text-slate-600">⚖️ 体重曲线</span>
          <span class="flex items-center gap-2 text-[11px] text-slate-400 flex-wrap">
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-red-400"></i>P3</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-orange-400"></i>P15</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-yellow-400"></i>P50</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-cyan-500"></i>P85</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-green-400"></i>P97</span>
            <span class="inline-flex items-center gap-1"
              ><i class="w-2 h-2 inline-block rounded-full bg-indigo-500"></i>孩子</span
            >
          </span>
        </div>
        <div ref="chartRefWeight" class="p-2" style="width: 100%; height: 300px"></div>
      </div>
    </div>

    <!-- BMI 曲线 + 身体状态说明 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-5">
      <div v-if="records.length" class="card overflow-hidden">
        <div
          class="px-4 py-2 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between flex-wrap gap-2"
        >
          <span class="text-xs font-semibold text-slate-600">🧮 BMI 曲线</span>
          <span v-if="ageMonths != null && ageMonths >= 84" class="flex items-center gap-2 text-[11px] text-slate-400">
            <span class="inline-flex items-center gap-1"
              ><i class="w-3 h-0.5 inline-block bg-amber-500"></i>超重界</span
            >
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-red-500"></i>肥胖界</span>
            <span class="inline-flex items-center gap-1"
              ><i class="w-2 h-2 inline-block rounded-full bg-indigo-500"></i>孩子</span
            >
          </span>
          <span v-else class="flex items-center gap-2 text-[11px] text-slate-400 flex-wrap">
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-red-400"></i>P3</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-orange-400"></i>P15</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-yellow-400"></i>P50</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-cyan-500"></i>P85</span>
            <span class="inline-flex items-center gap-1"><i class="w-3 h-0.5 inline-block bg-green-400"></i>P97</span>
            <span class="inline-flex items-center gap-1"
              ><i class="w-2 h-2 inline-block rounded-full bg-indigo-500"></i>孩子</span
            >
          </span>
        </div>
        <div ref="chartRefBMI" class="p-2" style="width: 100%; height: 300px"></div>
      </div>
      <div v-if="currentBmiInfo" class="card overflow-hidden border" :class="currentBmiInfo.advice.bg">
        <div class="px-4 py-3 flex items-center justify-between flex-wrap gap-2" :class="'bg-white/40'">
          <div class="flex items-center gap-2">
            <span class="text-base">💡</span>
            <span class="text-sm font-semibold text-slate-800">身体状态说明</span>
          </div>
          <span v-if="latestRecord" class="text-xs text-slate-500">{{ latestRecord.record_date }}</span>
        </div>
        <div class="p-4">
          <div class="flex items-center gap-3 mb-3 flex-wrap">
            <span
              class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold shadow-sm"
              :class="bmiColorClass"
            >
              {{ currentBmiInfo.assessment.label }}
            </span>
            <span class="text-xs text-slate-500">
              BMI <strong class="font-mono text-slate-700">{{ latestBMI?.toFixed?.(1) ?? latestBMI }}</strong>
              <span v-if="ageMonths != null" class="ml-1">· {{ ageDisplay(ageMonths) }}</span>
            </span>
          </div>
          <p class="text-sm mb-3 leading-relaxed font-medium" :class="currentBmiInfo.advice.tone">
            {{ currentBmiInfo.advice.desc }}
          </p>
          <div class="rounded-xl bg-white/70 border border-slate-200/70 p-3 mb-3">
            <p class="text-xs text-slate-600 leading-relaxed">
              <span class="font-semibold text-slate-700">✨ 给孩子的建议：</span>{{ currentBmiInfo.advice.advice }}
            </p>
          </div>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            📖 依据：{{ currentBmiInfo.assessment.source }}
            <template v-if="currentBmiInfo.assessment.cutoff">
              · 本年龄超重界 <span class="font-mono font-medium">{{ currentBmiInfo.assessment.cutoff[0] }}</span> /
              肥胖界
              <span class="font-mono font-medium">{{ currentBmiInfo.assessment.cutoff[1] }}</span>
            </template>
            <template v-if="currentBmiInfo.assessment.thinCutoff">
              · 消瘦界（轻度上限）
              <span class="font-mono font-medium">{{ currentBmiInfo.assessment.thinCutoff[1] }}</span>
            </template>
            <span v-if="!currentBmiInfo.assessment.cutoff">（百分位法，阈值随年龄/性别自动判定）</span>
          </p>
        </div>
      </div>
    </div>

    <!-- 标准对照表 -->
    <div v-if="yearlyStandards.length" class="card mb-5 overflow-hidden">
      <div
        class="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-brand-50/70 to-transparent flex items-center justify-between flex-wrap gap-2"
      >
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-brand-600">📐</span>
          <span class="text-sm font-semibold text-slate-800">身高体重标准对照表</span>
          <span class="text-xs text-slate-400 ml-1">
            {{ (childStore.current?.gender || "male") === "male" ? "男童" : "女童" }} · WS/T 423-2022 + WS/T 612-2018
          </span>
        </div>
        <span v-if="currentMonthIndex >= 0" class="text-[11px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full">
          📍 当前年龄（高亮行）
        </span>
      </div>
      <div class="overflow-x-auto px-2 py-2">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-100">
              <th class="text-left py-2 px-3 text-slate-500 font-medium">年龄</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium" colspan="5">📏 身高 (cm)</th>
              <th class="text-left py-2 px-3 text-slate-500 font-medium" colspan="5">⚖️ 体重 (kg)</th>
            </tr>
            <tr class="border-b border-slate-100">
              <th class="py-1 px-3"></th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P3</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P15</th>
              <th class="text-left py-1 px-3 text-xs text-slate-500 font-semibold">P50</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P85</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P97</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P3</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">
                P15<span v-if="rowHas3OnlyWeight" class="text-slate-300">*</span>
              </th>
              <th class="text-left py-1 px-3 text-xs text-slate-500 font-semibold">P50</th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">
                P85<span v-if="rowHas3OnlyWeight" class="text-slate-300">*</span>
              </th>
              <th class="text-left py-1 px-3 text-xs text-slate-400">P97</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in yearlyStandards"
              :key="row.months"
              class="border-b border-slate-50 transition hover:bg-slate-50"
              :class="currentMonthIndex === i ? 'bg-indigo-50' : ''"
            >
              <td class="py-2 px-3 font-medium" :class="currentMonthIndex === i ? 'text-indigo-700' : 'text-slate-700'">
                {{ row.label }}
                <span v-if="currentMonthIndex === i" class="ml-1 text-xs">📍</span>
              </td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.height.p3 }}</td>
              <td class="py-2 px-3 font-mono text-slate-500">{{ row.height.p15 ?? "—" }}</td>
              <td class="py-2 px-3 font-mono font-bold text-brand-700">{{ row.height.p50 }}</td>
              <td class="py-2 px-3 font-mono text-slate-500">{{ row.height.p85 ?? "—" }}</td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.height.p97 }}</td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.weight.p3 }}</td>
              <td class="py-2 px-3 font-mono text-slate-500">{{ row.weight.p15 ?? "—" }}</td>
              <td class="py-2 px-3 font-mono font-bold text-emerald-700">{{ row.weight.p50 }}</td>
              <td class="py-2 px-3 font-mono text-slate-500">{{ row.weight.p85 ?? "—" }}</td>
              <td class="py-2 px-3 font-mono text-slate-600">{{ row.weight.p97 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-3 pb-2 text-[11px] text-slate-400">
        <span v-if="hasThreeColWeight" class="text-amber-600">*</span> 该年龄段体重仅 3 档（国内暂无统一国标，参考首都儿科所九市调查 2009）
      </div>
    </div>

    <div v-if="loading" class="flex items-center justify-center py-14 text-slate-400 gap-2">
      <span class="inline-block w-4 h-4 border-2 border-slate-300 border-t-brand-600 rounded-full animate-spin"></span>
      <span class="text-sm">加载中…</span>
    </div>
    <div v-else-if="!records.length" class="card p-12 text-center">
      <div class="text-5xl mb-3">📏</div>
      <div class="text-base font-medium text-slate-600 mb-1">还没有生长发育记录</div>
      <div class="text-sm text-slate-400 mb-5">记录身高、体重、BMI，系统将自动对照儿童生长标准生成曲线与评估</div>
      <button class="btn-primary" @click="openCreate">+ 添加第一条记录</button>
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
          <!-- 备注字段已隐藏（华哥 2026-09-05 反馈）：
               后端 note 字段保留，编辑时仍写入空字符串以保持兼容。
               历史 note 数据不动，仅 UI 屏蔽录入和展示。 -->
        </div>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>
  </div>
</template>
