<script setup>
import { computed } from "vue"

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] }, // [{ name, type, smooth, data:[[date,value]...], lineStyle?, itemStyle? }]
  title: { type: String, default: "" },
})

// 给"分数"系列自动分配颜色，"班均"系列固定灰色虚线
const PALETTE = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]

const option = computed(() => {
  // 按科目分组：每科目的"分数"和"班均"成对
  let colorIdx = 0
  const styledSeries = props.series.map((s) => {
    const isAvg = (s.name || "").endsWith("-班均")
    const base = {
      ...s,
      type: "line",
      smooth: true,
      symbol: "circle",
      symbolSize: isAvg ? 5 : 6,
    }
    if (isAvg) {
      // 班级平均线：灰色虚线
      return {
        ...base,
        lineStyle: { ...(s.lineStyle || {}), type: "dashed", width: 1.5 },
        itemStyle: { color: "#94a3b8", ...(s.itemStyle || {}) },
        z: 1,
      }
    } else {
      // 分数线：彩色实线
      const color = PALETTE[colorIdx % PALETTE.length]
      colorIdx += 1
      return {
        ...base,
        lineStyle: { width: 2.5, ...(s.lineStyle || {}) },
        itemStyle: { color, ...(s.itemStyle || {}) },
        z: 2,
      }
    }
  })

  return {
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        if (!params || !params.length) return ""
        const date = new Date(params[0].value[0])
        const dateStr = `${date.getMonth() + 1}-${date.getDate()}`
        const lines = [`<div style="font-weight:600;margin-bottom:4px">${dateStr}</div>`]
        params.forEach((p) => {
          lines.push(
            `<div style="display:flex;align-items:center;gap:6px;font-size:12px;margin:2px 0">` +
              `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>` +
              `<span>${p.seriesName}: <strong>${p.value[1].toFixed(1)}%</strong></span>` +
              `</div>`,
          )
        })
        return lines.join("")
      },
    },
    legend: { top: 8, icon: "circle" },
    grid: { top: 50, right: 24, bottom: 30, left: 40 },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: "#e2e8f0" } },
      axisLabel: {
        color: "#64748b",
        fontSize: 11,
        formatter: (val) => {
          const d = new Date(val)
          return `${d.getMonth() + 1}-${d.getDate()}`
        },
      },
    },
    yAxis: {
      type: "value",
      // 若数据集中在 50+ / 40+，压缩底部空白，放大波动视觉
      min: (() => {
        const vals = props.series.flatMap((s) => s.data.map((d) => d[1]))
        if (!vals.length) return 0
        const m = Math.min(...vals)
        if (m >= 50) return 50
        if (m >= 40) return 40
        return 0
      })(),
      max: 100,
      axisLine: { show: false },
      axisLabel: { color: "#64748b", fontSize: 11, formatter: "{value}%" },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: styledSeries,
    title: props.title ? { text: props.title, left: "left", textStyle: { fontSize: 14, fontWeight: 600 } } : undefined,
  }
})
</script>

<template>
  <BaseChart :option="option" />
</template>

<script>
import BaseChart from "./BaseChart.vue"
export default { components: { BaseChart } }
</script>
