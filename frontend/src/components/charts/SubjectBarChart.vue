<script setup>
import { computed } from "vue";

const props = defineProps({
  subjects: { type: Array, default: () => [] }, // ['语文', '数学']
  avg: { type: Array, default: () => [] },
  latest: { type: Array, default: () => [] },
});

const option = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  legend: { top: 6, icon: "circle" },
  grid: { top: 50, right: 16, bottom: 30, left: 40 },
  xAxis: { type: "category", data: props.subjects, axisLine: { lineStyle: { color: "#e2e8f0" } }, axisLabel: { color: "#64748b" } },
  yAxis: { type: "value", max: 100, axisLine: { show: false }, axisLabel: { color: "#64748b", formatter: "{value}%" }, splitLine: { lineStyle: { color: "#f1f5f9" } } },
  series: [
    {
      name: "平均分",
      type: "bar",
      data: props.avg,
      barWidth: 18,
      itemStyle: { color: "#a5b4fc", borderRadius: [4, 4, 0, 0] },
    },
    {
      name: "最近一次",
      type: "bar",
      data: props.latest,
      barWidth: 18,
      itemStyle: { color: "#6366f1", borderRadius: [4, 4, 0, 0] },
    },
  ],
}));
</script>

<template>
  <BaseChart :option="option" height="280px" />
</template>

<script>
import BaseChart from "./BaseChart.vue";
export default { components: { BaseChart } };
</script>
