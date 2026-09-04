<script setup>
import { computed } from "vue"
import { useChildStore } from "@/stores/child"
import { useAuthStore } from "@/stores/auth"
import { useRouter } from "vue-router"

const childStore = useChildStore()
const auth = useAuthStore()
const router = useRouter()

const current = computed(() => childStore.current)
const isChild = computed(() => auth.isChild)

const goToChildren = () => router.push("/children")
</script>

<template>
  <!-- 孩子账号：只读展示自己，不提供切换/添加 -->
  <div v-if="isChild" class="px-1 py-2">
    <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2">当前账号</div>
    <div class="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2">
      <div
        class="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-medium"
        :style="{ backgroundColor: auth.user?.avatar_color || '#6366f1' }"
      >
        {{ (auth.user?.display_name || "?").charAt(0) }}
      </div>
      <span class="text-sm text-slate-700 font-medium">{{ auth.user?.display_name }}</span>
    </div>
  </div>

  <!-- 家长账号：原逻辑 -->
  <template v-else>
    <div v-if="!current" class="text-center py-3">
      <button class="btn-primary w-full text-sm" @click="goToChildren">+ 添加孩子档案</button>
    </div>

    <div v-else>
      <div class="text-[11px] uppercase tracking-wider text-slate-400 font-medium mb-2 px-1">当前孩子</div>
      <el-select
        :model-value="current.id"
        class="w-full"
        size="default"
        @update:model-value="(v) => childStore.setCurrent(v)"
      >
        <el-option v-for="c in childStore.children" :key="c.id" :label="`${c.name} · ${c.grade}`" :value="c.id">
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
</template>
