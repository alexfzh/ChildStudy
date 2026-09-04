<script setup>
import { ref, computed, watch } from "vue"
import { PRESET_SUBJECTS, PRESET_SUBJECTS_SET, SUBJECT_COLOR_MAP, CUSTOM_SUBJECT_COLOR } from "@/constants/subjects"

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(["update:modelValue"])

const selected = computed(() => props.modelValue || [])
const customSubjects = computed(() => selected.value.filter((s) => !PRESET_SUBJECTS_SET.has(s)))
const customActive = ref(customSubjects.value.length > 0) // 如果已有自定义，自动展开输入区

const customInput = ref("")
const customError = ref("")

watch(
  () => customSubjects.value.length,
  (n) => {
    // 自定义清空后收起输入区
    if (n === 0) customActive.value = false
  },
)

const isPresetSelected = (name) => selected.value.includes(name)

const togglePreset = (name) => {
  const next = [...selected.value]
  const idx = next.indexOf(name)
  if (idx >= 0) {
    next.splice(idx, 1)
  } else {
    next.push(name)
  }
  emit("update:modelValue", next)
}

const removeCustom = (name) => {
  emit(
    "update:modelValue",
    selected.value.filter((s) => s !== name),
  )
}

const submitCustom = () => {
  const v = customInput.value.trim()
  if (!v) return
  if (v.length > 16) {
    customError.value = "科目名不能超过 16 字"
    return
  }
  if (PRESET_SUBJECTS_SET.has(v)) {
    customError.value = "这是预设科目，请直接点选"
    return
  }
  if (selected.value.includes(v)) {
    customError.value = "已添加过这个科目"
    return
  }
  emit("update:modelValue", [...selected.value, v])
  customInput.value = ""
  customError.value = ""
}

const cancelCustom = () => {
  customActive.value = false
  customInput.value = ""
  customError.value = ""
}

const colorFor = (name) =>
  PRESET_SUBJECTS_SET.has(name)
    ? SUBJECT_COLOR_MAP[name] || "bg-slate-100 text-slate-700 border-slate-200"
    : CUSTOM_SUBJECT_COLOR
</script>

<template>
  <div>
    <!-- 预设 chip -->
    <div class="flex flex-wrap gap-2">
      <button
        v-for="name in PRESET_SUBJECTS"
        :key="name"
        type="button"
        :class="[
          'px-3 py-1.5 rounded-full text-sm border transition select-none',
          isPresetSelected(name)
            ? 'bg-brand-500 text-white border-brand-500 shadow-sm'
            : 'bg-white text-slate-600 border-slate-200 hover:border-brand-300 hover:bg-brand-50',
        ]"
        @click="togglePreset(name)"
      >
        {{ name }}
      </button>

      <!-- 「+ 自定义」按钮 -->
      <button
        v-if="!customActive"
        type="button"
        class="px-3 py-1.5 rounded-full text-sm border border-dashed border-slate-300 text-slate-500 hover:border-brand-400 hover:text-brand-600 hover:bg-brand-50 transition"
        @click="customActive = true"
      >
        + 自定义
      </button>
    </div>

    <!-- inline 自定义输入框 -->
    <div v-if="customActive" class="mt-3 flex items-center gap-2 max-w-md">
      <el-input
        v-model="customInput"
        placeholder="输入科目名（≤16字），回车提交"
        maxlength="16"
        clearable
        @keyup.enter="submitCustom"
        @input="customError = ''"
      />
      <button class="btn-secondary text-sm flex-shrink-0" @click="submitCustom">添加</button>
      <button v-if="customSubjects.length === 0" class="btn-ghost text-sm flex-shrink-0" @click="cancelCustom">
        取消
      </button>
    </div>
    <div v-if="customError" class="text-xs text-rose-600 mt-1">{{ customError }}</div>

    <!-- 已选自定义 -->
    <div v-if="customSubjects.length > 0" class="mt-3">
      <div class="text-xs text-slate-500 mb-1.5">自定义科目：</div>
      <div class="flex flex-wrap gap-1.5">
        <span
          v-for="s in customSubjects"
          :key="s"
          :class="['inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border', colorFor(s)]"
        >
          {{ s }}
          <button
            type="button"
            class="opacity-60 hover:opacity-100 leading-none"
            :title="`移除 ${s}`"
            @click="removeCustom(s)"
          >
            ×
          </button>
        </span>
      </div>
    </div>
  </div>
</template>
