<script setup>
import { onMounted, ref } from "vue";
import { dashboardAPI } from "@/api";

const compareData = ref(null);

const loadCompare = async () => {
  try {
    compareData.value = await dashboardAPI.compare();
  } catch (e) {
    /* noop */
  }
};

onMounted(loadCompare);
</script>

<template>
  <div class="space-y-5">
    <!-- 多孩子对比 -->
    <div v-if="compareData && compareData.children.length > 1" class="card p-5">
      <h3 class="font-semibold text-slate-800 mb-1">多孩子对比</h3>
      <p class="text-sm text-slate-500 mb-4">非排名导向，呈现各自的优势与需要关注的领域</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div v-for="c in compareData.children" :key="c.id" class="p-4 rounded-xl border border-slate-200">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-9 h-9 rounded-full flex items-center justify-center text-white font-medium"
                 :style="{ backgroundColor: c.avatar_color }">{{ c.name.charAt(0) }}</div>
            <div>
              <div class="font-medium text-slate-800">{{ c.name }}</div>
              <div class="text-xs text-slate-500">{{ c.grade }} · {{ c.total_exams }} 次考试</div>
            </div>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between"><span class="text-slate-500">平均分</span><span class="font-medium">{{ c.average_score }}%</span></div>
            <div class="flex justify-between"><span class="text-slate-500">最强科目</span><span class="font-medium text-emerald-600">{{ c.best_subject || "—" }}</span></div>
            <div class="flex justify-between"><span class="text-slate-500">需要关注</span><span class="font-medium text-amber-600">{{ c.needs_attention_subject || "—" }}</span></div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="card p-8 text-center text-sm text-slate-400">
      暂无多个孩子的数据可对比
    </div>
  </div>
</template>
