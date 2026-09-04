<script setup>
import { ref, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import dayjs from "dayjs"
import { useChildStore } from "@/stores/child"
import { examsAPI, knowledgePointsAPI, importExportAPI, rewardsAPI } from "@/api"
import { PRESET_SUBJECTS } from "@/constants/subjects"

const route = useRoute()
const router = useRouter()
const childStore = useChildStore()

const loading = ref(false)
const exams = ref([])
const filterSubject = ref("")
const filterType = ref("")
const filterKnowledgePoint = ref("")

const blank = () => ({
  child_id: childStore.currentId,
  subject: "",
  exam_name: "",
  exam_type: "quiz",
  score: 0,
  full_score: 100,
  target_score: null,
  class_average: null,
  class_rank: null,
  grade_rank: null,
  exam_date: dayjs().format("YYYY-MM-DD"),
  knowledge_points: [],
  wrong_questions: "",
  teacher_comment: "",
  note: "",
})

const form = ref(blank())
const dialogVisible = ref(false)
const editing = ref(null)
const kpInput = ref("")
const allKnowledgePoints = ref([])

const kpOptions = computed(() => {
  const set = new Set(allKnowledgePoints.value)
  form.value.knowledge_points?.forEach((k) => set.add(k))
  return Array.from(set).filter((k) => !form.value.knowledge_points?.includes(k))
})

const fetchKnowledgePoints = async () => {
  try {
    allKnowledgePoints.value = await knowledgePointsAPI.list({
      subject: form.value.subject || undefined,
    })
  } catch {
    // 知识点库加载失败不影响主流程
  }
}

const fetchList = async () => {
  if (!childStore.currentId) return
  loading.value = true
  try {
    exams.value = await examsAPI.list({
      child_id: childStore.currentId,
      subject: filterSubject.value || undefined,
      knowledge_point: filterKnowledgePoint.value || undefined,
    })
    // 同步更新知识点候选集(用于筛选下拉)
    const set = new Set()
    exams.value.forEach((e) => (e.knowledge_points || []).forEach((k) => set.add(k)))
    allKnowledgePoints.value = Array.from(set).sort()
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await fetchList()
  if (route.query.action === "new") openCreate()
})

watch(() => childStore.currentId, fetchList)
watch([filterSubject, filterType, filterKnowledgePoint], fetchList)

const openCreate = () => {
  editing.value = null
  form.value = blank()
  dialogVisible.value = true
  fetchKnowledgePoints()
}

const openEdit = (e) => {
  editing.value = e
  form.value = { ...blank(), ...e, knowledge_points: [...(e.knowledge_points || [])] }
  dialogVisible.value = true
  fetchKnowledgePoints()
}

const addKp = () => {
  const v = kpInput.value.trim()
  if (v && !form.value.knowledge_points.includes(v)) {
    form.value.knowledge_points.push(v)
  }
  kpInput.value = ""
}
const removeKp = (i) => form.value.knowledge_points.splice(i, 1)

const submit = async () => {
  if (!form.value.subject || !form.value.exam_name) {
    ElMessage.warning("请填写科目和考试名称")
    return
  }
  if (editing.value) {
    await examsAPI.update(editing.value.id, form.value)
    ElMessage.success("已更新")
  } else {
    const created = await examsAPI.create(form.value)
    ElMessage.success("已录入")
    // 触发奖励计算
    try {
      const reward = await rewardsAPI.examReward(created.id)
      if (reward.points_earned > 0) {
        ElMessage.success(`🎉 +${reward.points_earned} 积分！`)
      }
      if (reward.new_achievements?.length) {
        reward.new_achievements.forEach((a) => {
          ElMessage.success(`🏆 解锁成就：${a.achievement?.name || "新成就"}`)
        })
      }
      if (reward.new_rank) {
        ElMessage.success(`🎖️ 段位提升：${reward.new_rank.tier} ⭐${reward.new_rank.stars}`)
      }
    } catch (e) {
      /* 奖励计算失败不影响录入 */
    }
  }
  dialogVisible.value = false
  await fetchList()
}

const remove = async (e) => {
  await ElMessageBox.confirm(`确认删除「${e.exam_name}」吗？`, "删除", { type: "warning" })
  await examsAPI.remove(e.id)
  ElMessage.success("已删除")
  await fetchList()
}

const subjectOptions = computed(() => {
  const set = new Set(PRESET_SUBJECTS)
  ;(childStore.current?.subjects || []).forEach((s) => set.add(s))
  exams.value.forEach((e) => set.add(e.subject))
  return Array.from(set)
})

const pct = (s, f) => Math.round((s / f) * 100)

const scoreColor = (p) =>
  p >= 85 ? "text-emerald-600" : p >= 70 ? "text-brand-600" : p >= 60 ? "text-amber-600" : "text-rose-600"
const scoreBg = (p) => (p >= 85 ? "bg-emerald-50" : p >= 70 ? "bg-brand-50" : p >= 60 ? "bg-amber-50" : "bg-rose-50")

// ============ 导入导出 ============
const importDialogVisible = ref(false)
const importFile = ref(null)
const importLoading = ref(false)

const doExport = async () => {
  try {
    const blob = await importExportAPI.exportExams({
      child_id: childStore.currentId,
      subject: filterSubject.value || undefined,
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `exams_${childStore.current?.name || "all"}_${dayjs().format("YYYYMMDD")}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success("导出成功")
  } catch (e) {
    /* axios 已提示 */
  }
}

const doImport = async () => {
  if (!importFile.value) {
    ElMessage.warning("请选择 CSV 文件")
    return
  }
  importLoading.value = true
  try {
    const res = await importExportAPI.importExams(importFile.value, childStore.currentId)
    ElMessage.success(res.message || "导入完成")
    importDialogVisible.value = false
    importFile.value = null
    await fetchList()
  } catch (e) {
    /* axios 已提示 */
  } finally {
    importLoading.value = false
  }
}
</script>

<template>
  <div v-if="!childStore.currentId" class="card p-10 text-center text-slate-500">请先在「孩子档案」中添加孩子</div>

  <div v-else>
    <div class="flex items-center justify-between mb-4 flex-wrap gap-2">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">考试管理</h2>
        <p class="text-sm text-slate-500 mt-0.5">记录每次考试/测验，分析进步轨迹</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-secondary" @click="doExport">📥 导出 CSV</button>
        <button class="btn-secondary" @click="importDialogVisible = true">📤 导入 CSV</button>
        <button class="btn-secondary" @click="router.push({ name: 'exam-analysis' })">📊 考试分析</button>
        <button class="btn-primary" @click="openCreate">+ 录入考试</button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="card p-3 mb-4 flex gap-2 flex-wrap items-center">
      <el-select v-model="filterSubject" placeholder="全部科目" clearable size="default" class="!w-40">
        <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="filterType" placeholder="全部类型" clearable size="default" class="!w-40">
        <el-option label="期中/期末" value="exam" />
        <el-option label="单元测验" value="quiz" />
        <el-option label="随堂测" value="homework" />
      </el-select>
      <el-select
        v-if="allKnowledgePoints.length"
        v-model="filterKnowledgePoint"
        placeholder="全部知识点"
        clearable
        size="default"
        class="!w-44"
      >
        <el-option v-for="k in allKnowledgePoints" :key="k" :label="k" :value="k" />
      </el-select>
      <span class="ml-auto text-xs text-slate-400 self-center">共 {{ exams.length }} 条</span>
    </div>

    <div v-if="loading" class="text-center py-10 text-slate-400">加载中…</div>
    <div v-else-if="exams.length === 0" class="card p-10 text-center text-slate-400">
      <div class="text-4xl mb-2">📝</div>
      <div class="text-sm">还没有考试记录</div>
    </div>

    <div v-else class="space-y-2">
      <div v-for="e in exams" :key="e.id" class="card p-4 hover:shadow-soft transition-shadow">
        <div class="flex items-start justify-between flex-wrap gap-2">
          <div class="flex items-start gap-3 flex-1 min-w-0">
            <div
              :class="[
                'w-14 h-14 rounded-xl flex flex-col items-center justify-center text-white font-semibold',
                scoreBg(pct(e.score, e.full_score)),
              ]"
            >
              <div :class="['text-xl', scoreColor(pct(e.score, e.full_score))]">{{ pct(e.score, e.full_score) }}</div>
              <div class="text-[10px] text-slate-500 mt-[-2px]">{{ e.score }}/{{ e.full_score }}</div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-slate-800">{{ e.exam_name }}</span>
                <span class="badge bg-slate-100 text-slate-600">{{ e.subject }}</span>
                <span class="badge bg-brand-50 text-brand-700">{{
                  { exam: "期中/期末", quiz: "单元测验", homework: "随堂测" }[e.exam_type]
                }}</span>
                <span
                  v-if="e.target_score != null"
                  class="badge"
                  :class="e.score >= e.target_score ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
                >
                  目标 {{ e.target_score }} · {{ e.score >= e.target_score ? "达标" : "未达" }}
                </span>
              </div>
              <div class="text-xs text-slate-400 mt-1.5 flex flex-wrap gap-x-3 items-center">
                <span>📅 {{ dayjs(e.exam_date).format("YYYY-MM-DD") }}</span>
                <span v-if="e.class_rank">班级 #{{ e.class_rank }}</span>
                <span v-if="e.grade_rank">年级 #{{ e.grade_rank }}</span>
                <span
                  v-if="e.class_average != null"
                  :class="[
                    'inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium',
                    e.score >= e.class_average ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700',
                  ]"
                >
                  班均 {{ e.class_average }} · {{ e.score >= e.class_average ? "高于" : "低于"
                  }}{{ Math.abs(e.score - e.class_average).toFixed(1) }}
                </span>
              </div>
            </div>
            <div v-if="e.target_score != null" class="mt-2">
              <div class="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                <span>实际 {{ e.score }}</span>
                <span>目标 {{ e.target_score }}</span>
              </div>
              <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :class="e.score >= e.target_score ? 'bg-emerald-500' : 'bg-amber-500'"
                  :style="`width:${Math.min((e.score / e.target_score) * 100, 100)}%`"
                ></div>
              </div>
            </div>
            <div v-if="e.knowledge_points?.length" class="flex flex-wrap gap-1 mt-2">
              <span v-for="k in e.knowledge_points" :key="k" class="badge bg-amber-50 text-amber-700">{{ k }}</span>
            </div>
            <div v-if="e.wrong_questions" class="text-xs text-slate-500 mt-2 leading-relaxed">
              <span class="text-slate-400">错题：</span>{{ e.wrong_questions }}
            </div>
            <div v-if="e.teacher_comment" class="text-xs text-slate-500 mt-1 leading-relaxed">
              <span class="text-slate-400">师评：</span>{{ e.teacher_comment }}
            </div>
          </div>
        </div>
        <div class="flex gap-1">
          <button
            class="btn-ghost text-xs text-brand-600"
            @click="router.push({ name: 'exam-analysis', query: { exam_id: e.id } })"
          >
            分析
          </button>
          <button class="btn-ghost text-xs" @click="openEdit(e)">编辑</button>
          <button class="btn-ghost text-xs text-rose-600" @click="remove(e)">删除</button>
        </div>
      </div>
    </div>
  </div>

  <!-- 表单对话框 -->
  <el-dialog v-model="dialogVisible" :title="editing ? '编辑考试' : '录入考试'" width="560px">
    <el-form label-position="top">
      <div class="grid grid-cols-2 gap-3">
        <el-form-item label="科目" required>
          <el-select
            v-model="form.subject"
            filterable
            placeholder="从下拉选，不能新建"
            class="w-full"
            @change="fetchKnowledgePoints"
          >
            <el-option v-for="s in subjectOptions" :key="s" :label="s" :value="s" />
          </el-select>
          <div class="text-xs text-slate-400 mt-1">
            💡 仅显示预设 + 你在孩子档案里选过的科目。新增科目请去「孩子档案」编辑
          </div>
        </el-form-item>
        <el-form-item label="考试名称" required>
          <el-input v-model="form.exam_name" placeholder="如：第三单元" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.exam_type" class="w-full">
            <el-option label="期中/期末" value="exam" />
            <el-option label="单元测验" value="quiz" />
            <el-option label="随堂测" value="homework" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker v-model="form.exam_date" value-format="YYYY-MM-DD" type="date" class="w-full" />
        </el-form-item>
        <el-form-item label="得分">
          <el-input-number v-model="form.score" :precision="1" :step="0.5" :min="0" class="!w-full" />
        </el-form-item>
        <el-form-item label="满分">
          <el-input-number v-model="form.full_score" :precision="1" :step="1" :min="1" class="!w-full" />
        </el-form-item>
        <el-form-item label="目标分数">
          <el-input-number
            v-model="form.target_score"
            :precision="1"
            :step="1"
            :min="0"
            class="!w-full"
            placeholder="不设则留空"
          />
        </el-form-item>
        <el-form-item label="班级平均分">
          <el-input-number
            v-model="form.class_average"
            :precision="1"
            :step="1"
            :min="0"
            class="!w-full"
            placeholder="不设则留空"
          />
        </el-form-item>
        <el-form-item label="班级排名">
          <el-input-number v-model="form.class_rank" :min="1" class="!w-full" />
        </el-form-item>
        <el-form-item label="年级排名">
          <el-input-number v-model="form.grade_rank" :min="1" class="!w-full" />
        </el-form-item>
      </div>

      <el-form-item label="知识点标签">
        <div class="flex gap-2 w-full">
          <el-select
            v-model="kpInput"
            filterable
            allow-create
            default-first-option
            placeholder="从标签库选或回车创建"
            class="flex-1"
            @keyup.enter="addKp"
          >
            <el-option v-for="k in kpOptions" :key="k" :label="k" :value="k" @click="addKp" />
          </el-select>
          <button class="btn-secondary" @click="addKp">添加</button>
        </div>
        <div class="flex flex-wrap gap-1.5 mt-2">
          <span
            v-for="(k, i) in form.knowledge_points"
            :key="i"
            class="badge bg-amber-50 text-amber-700 cursor-pointer"
            @click="removeKp(i)"
          >
            {{ k }} ×
          </span>
        </div>
        <div class="text-xs text-slate-400 mt-1">💡 从已有标签库选取，或直接输入新知识点后回车</div>
      </el-form-item>

      <el-form-item label="错题简述（便于后续分析）">
        <el-input
          v-model="form.wrong_questions"
          type="textarea"
          :rows="2"
          placeholder="如：应用题单位换算混淆、解方程移项忘记变号"
        />
      </el-form-item>
      <el-form-item label="老师评语">
        <el-input v-model="form.teacher_comment" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <button class="btn-ghost" @click="dialogVisible = false">取消</button>
      <button class="btn-primary ml-2" @click="submit">保存</button>
    </template>
  </el-dialog>

  <!-- 导入对话框 -->
  <el-dialog v-model="importDialogVisible" title="导入考试 CSV" width="480px">
    <div class="space-y-3">
      <div class="text-sm text-slate-600">
        当前孩子：<span class="font-medium">{{ childStore.current?.name }}</span
        >（{{ childStore.current?.grade }}）
      </div>
      <el-alert title="CSV 必须包含列：subject, exam_name, score, exam_date" type="info" :closable="false" />
      <el-form label-position="top">
        <el-form-item label="选择 CSV 文件">
          <input type="file" accept=".csv" @change="(e) => (importFile.value = e.target.files[0])" />
        </el-form-item>
      </el-form>
      <div class="text-xs text-slate-400">
        💡 先点击「导出 CSV」下载模板，按格式填写后上传。系统会自动按当前孩子导入。
      </div>
    </div>
    <template #footer>
      <button class="btn-ghost" @click="importDialogVisible = false">取消</button>
      <button class="btn-primary ml-2" :loading="importLoading" @click="doImport">开始导入</button>
    </template>
  </el-dialog>
</template>
