<script setup>
import { ref, computed, onMounted } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useChildStore } from "@/stores/child"
import { socialEmotionalAPI } from "@/api"

const childStore = useChildStore()
const childId = computed(() => childStore.current?.id)

const loading = ref(false)
const records = ref([])

const dialogVisible = ref(false)
const editing = ref(null)

const emotionTagOptions = ["happy", "calm", "anxious", "angry", "sad", "excited", "nervous", "proud"]

const blankForm = () => ({
  record_date: new Date().toISOString().slice(0, 10),
  mood_score: "",
  emotion_tags: [],
  social_activity: "",
  confidence_level: "",
  note: "",
})

const form = ref(blankForm())

const fetchList = async () => {
  if (!childId.value) return
  loading.value = true
  try {
    records.value = await socialEmotionalAPI.list(childId.value)
  } finally {
    loading.value = false
  }
}

onMounted(fetchList)

const openCreate = () => {
  editing.value = null
  form.value = blankForm()
  dialogVisible.value = true
}

const openEdit = (r) => {
  editing.value = r
  form.value = {
    record_date: r.record_date,
    mood_score: r.mood_score ?? "",
    emotion_tags: [...(r.emotion_tags || [])],
    social_activity: r.social_activity ?? "",
    confidence_level: r.confidence_level ?? "",
    note: r.note ?? "",
  }
  dialogVisible.value = true
}

const submit = async () => {
  const data = {
    ...form.value,
    mood_score: form.value.mood_score ? Number(form.value.mood_score) : null,
    confidence_level: form.value.confidence_level ? Number(form.value.confidence_level) : null,
  }
  try {
    if (editing.value) {
      await socialEmotionalAPI.update(editing.value.id, data)
      ElMessage.success("已更新")
    } else {
      await socialEmotionalAPI.create(childId.value, data)
      ElMessage.success("已添加")
    }
    dialogVisible.value = false
    await fetchList()
  } catch (e) {
    /* axios 已提示 */
  }
}

const remove = async (r) => {
  await ElMessageBox.confirm(`确认删除 ${r.record_date} 的社交情感记录吗？`, "删除", { type: "warning" })
  await socialEmotionalAPI.remove(r.id)
  ElMessage.success("已删除")
  await fetchList()
}

const moodEmoji = (s) => {
  const map = { 1: "😢", 2: "😟", 3: "😐", 4: "🙂", 5: "😄" }
  return map[s] || "❓"
}

const latestMood = computed(() => records.value[0]?.mood_score)
const latestConfidence = computed(() => records.value[0]?.confidence_level)
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">社交情感</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录情绪、社交活动、自信心发展</p>
      </div>
      <button class="btn-primary" @click="openCreate">+ 添加记录</button>
    </div>

    <!-- 最新数据卡片 -->
    <div v-if="records.length" class="grid grid-cols-2 md:grid-cols-3 gap-3 mb-5">
      <div class="card p-4">
        <div class="text-xs text-slate-500">当前情绪</div>
        <div class="text-3xl mt-1">{{ moodEmoji(latestMood) }}</div>
        <div class="text-xs text-slate-400 mt-1">{{ latestMood ? latestMood + "/5" : "-" }}</div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">自信心</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">
          {{ latestConfidence ? latestConfidence + "/5" : "-" }}
        </div>
      </div>
      <div class="card p-4">
        <div class="text-xs text-slate-500">记录次数</div>
        <div class="text-2xl font-semibold text-slate-800 mt-1">{{ records.length }} 次</div>
      </div>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="!records.length" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">💭</div>
      <div class="text-sm">还没有记录，点击右上角添加</div>
    </div>

    <div v-else class="card overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-slate-100">
            <th class="text-left py-3 px-4 text-slate-500 font-medium">日期</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">情绪</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">情绪标签</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">社交活动</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">自信心</th>
            <th class="text-left py-3 px-4 text-slate-500 font-medium">备注</th>
            <th class="text-right py-3 px-4 text-slate-500 font-medium">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id" class="border-b border-slate-50 hover:bg-slate-50">
            <td class="py-3 px-4">{{ r.record_date }}</td>
            <td class="py-3 px-4">{{ moodEmoji(r.mood_score) }} {{ r.mood_score ?? "-" }}/5</td>
            <td class="py-3 px-4">
              <span
                v-for="tag in r.emotion_tags || []"
                :key="tag"
                class="inline-block px-2 py-0.5 rounded bg-brand-50 text-brand-700 text-xs mr-1 mb-1"
                >{{ tag }}</span
              >
              <span v-if="!r.emotion_tags?.length">-</span>
            </td>
            <td class="py-3 px-4">{{ r.social_activity || "-" }}</td>
            <td class="py-3 px-4">{{ r.confidence_level ? r.confidence_level + "/5" : "-" }}</td>
            <td class="py-3 px-4 text-slate-400 max-w-[200px] truncate">{{ r.note || "-" }}</td>
            <td class="py-3 px-4 text-right">
              <button class="text-xs text-brand-600 hover:text-brand-700 mr-2" @click="openEdit(r)">编辑</button>
              <button class="text-xs text-rose-600 hover:text-rose-700" @click="remove(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑记录' : '添加记录'" width="480px">
      <el-form label-position="top">
        <div class="grid grid-cols-2 gap-3">
          <el-form-item label="日期" required>
            <el-input v-model="form.record_date" type="date" />
          </el-form-item>
          <el-form-item label="情绪指数 (1-5)">
            <el-select v-model="form.mood_score" placeholder="选择" clearable class="w-full">
              <el-option v-for="n in 5" :key="n" :label="`${n} - ${moodEmoji(n)}`" :value="n" />
            </el-select>
          </el-form-item>
          <el-form-item label="情绪标签">
            <el-select v-model="form.emotion_tags" multiple filterable allow-create class="w-full">
              <el-option v-for="t in emotionTagOptions" :key="t" :label="t" :value="t" />
            </el-select>
          </el-form-item>
          <el-form-item label="社交活动">
            <el-input v-model="form.social_activity" placeholder="如：和同学打球、参加生日派对" />
          </el-form-item>
          <el-form-item label="自信心 (1-5)">
            <el-select v-model="form.confidence_level" placeholder="选择" clearable class="w-full">
              <el-option v-for="n in 5" :key="n" :label="`${n}/5`" :value="n" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注" class="col-span-2">
            <el-input v-model="form.note" type="textarea" :rows="2" />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>
  </div>
</template>
