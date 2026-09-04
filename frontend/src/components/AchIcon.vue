<script setup>
import { computed } from "vue"

const props = defineProps({
  icon: { type: String, default: "" },
})

// 自定义 SVG 图标：icon 字段以 "svg:" 开头时按 key 渲染矢量图标
const CUSTOM_SVGS = {
  // 金色小桶（第一桶金）
  "gold-bucket": `<svg width="1em" height="1em" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg" style="vertical-align:-0.15em">
    <defs>
      <linearGradient id="achGoldG" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#FFE082"/>
        <stop offset="0.55" stop-color="#FFC107"/>
        <stop offset="1" stop-color="#B8860B"/>
      </linearGradient>
    </defs>
    <path d="M15 21 Q32 1 49 21" fill="none" stroke="#C79100" stroke-width="4.5" stroke-linecap="round"/>
    <path d="M13 25 Q32 33 51 25 L46 54 Q32 61 18 54 Z" fill="url(#achGoldG)"/>
    <ellipse cx="32" cy="25" rx="19.5" ry="6.5" fill="#8B5E00"/>
    <ellipse cx="32" cy="23.2" rx="19.5" ry="6.5" fill="url(#achGoldG)"/>
    <path d="M23 31 Q26 42 27.5 50" stroke="#FFF3C4" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.75"/>
  </svg>`,
}

const svg = computed(() => {
  const raw = props.icon || ""
  if (raw.startsWith("svg:")) return CUSTOM_SVGS[raw.slice(4)] || null
  return null
})
</script>

<template>
  <span v-if="svg" class="inline-block align-middle leading-none" v-html="svg" />
  <span v-else class="inline-block align-middle leading-none">{{ icon }}</span>
</template>
