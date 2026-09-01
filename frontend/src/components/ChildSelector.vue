<script setup>
import { computed } from "vue";
import { useChildStore } from "@/stores/child";
import { useRouter } from "vue-router";

const childStore = useChildStore();
const router = useRouter();

const current = computed(() => childStore.current);

const goToChildren = () => router.push("/children");
</script>

<template>
  <div v-if="!current" class="text-center py-3">
    <button class="btn-primary w-full text-sm" @click="goToChildren">
      + 添加孩子档案
    </button>
  </div>

  <div v-else>
    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2 px-1">
      当前孩子
    </div>
    <el-select
      :model-value="current.id"
      @update:model-value="(v) => childStore.setCurrent(v)"
      class="w-full"
      size="default"
    >
      <el-option
        v-for="c in childStore.children"
        :key="c.id"
        :label="`${c.name} · ${c.grade}`"
        :value="c.id"
      >
        <div class="flex items-center gap-2">
          <div
            class="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-medium"
            :style="{ backgroundColor: c.avatar_color }"
          >
            {{ c.name.charAt(0) }}
          </div>
          <span>{{ c.name }}</span>
          <span class="text-xs text-slate-400 ml-auto">{{ c.grade }}</span>
        </div>
      </el-option>
    </el-select>
  </div>
</template>
