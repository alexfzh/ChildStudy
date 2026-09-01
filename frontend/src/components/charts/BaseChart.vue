<script setup>
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, BarChart, RadarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  RadarComponent,
  MarkLineComponent,
  MarkAreaComponent,
} from "echarts/components";

use([
  CanvasRenderer, LineChart, BarChart, RadarChart,
  GridComponent, TooltipComponent, LegendComponent, TitleComponent,
  RadarComponent, MarkLineComponent, MarkAreaComponent,
]);

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: "320px" },
});

const chartStyle = computed(() => ({ height: props.height, width: "100%" }));
</script>

<template>
  <v-chart :option="option" :style="chartStyle" autoresize />
</template>
