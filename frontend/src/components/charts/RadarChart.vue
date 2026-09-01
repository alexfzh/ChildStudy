<script setup>
import { computed } from "vue";

const props = defineProps({
  indicators: { type: Array, default: () => [] }, // [{ name, max }]
  values: { type: Array, default: () => [] },
  title: { type: String, default: "能力雷达图" },
});

const option = computed(() => ({
  title: { text: props.title, left: "center", top: 6, textStyle: { fontSize: 14, fontWeight: 600 } },
  tooltip: { trigger: "item" },
  radar: {
    indicator: props.indicators,
    center: ["50%", "55%"],
    radius: "62%",
    splitArea: { areaStyle: { color: ["#fafbff", "#fff"] } },
    axisLine: { lineStyle: { color: "#e2e8f0" } },
    splitLine: { lineStyle: { color: "#e2e8f0" } },
    axisName: { color: "#475569", fontSize: 12 },
  },
  series: [{
    type: "radar",
    data: [{
      value: props.values,
      name: "平均得分率",
      symbol: "circle",
      symbolSize: 5,
      lineStyle: { color: "#6366f1", width: 2 },
      areaStyle: { color: "rgba(99, 102, 241, 0.18)" },
      itemStyle: { color: "#6366f1" },
    }],
  }],
}));
</script>

<template>
  <BaseChart :option="option" height="320px" />
</template>

<script>
import BaseChart from "./BaseChart.vue";
export default { components: { BaseChart } };
</script>
