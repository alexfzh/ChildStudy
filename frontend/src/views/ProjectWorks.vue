<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-800">🎨 单元 Big Task</h1>
        <p class="text-sm text-slate-500 mt-1">
          提交每个 Unit 的作品（写诗 / 制作 animal profile / 拍照片 / 调查等）— 家长点评 + 集成时间轴
        </p>
      </div>
      <el-button type="primary" @click="showSubmitDialog = true"> <span class="mr-1">+</span> 提交作品 </el-button>
    </div>

    <el-card shadow="never" class="!border-slate-200">
      <div class="flex flex-wrap gap-3 items-center">
        <el-select v-model="filterUnitId" placeholder="按教材单元筛选" clearable class="!w-60" @change="reload">
          <el-option v-for="u in units" :key="u.id" :label="`${u.code} ${u.title_en}`" :value="u.id" />
        </el-select>
        <el-select v-model="filterStatus" placeholder="状态" clearable class="!w-40" @change="reload">
          <el-option label="已提交" value="submitted" />
          <el-option label="已点评" value="reviewed" />
          <el-option label="已通过" value="approved" />
          <el-option label="待修改" value="needs_revision" />
        </el-select>
      </div>
    </el-card>

    <div v-loading="loading">
      <el-empty v-if="!loading && works.length === 0" description="还没有作品，鼓励孩子完成 Big Task！" />
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <el-card v-for="w in works" :key="w.id" shadow="hover" class="!border-slate-200">
          <div class="flex items-start justify-between">
            <div class="flex-1 min-w-0">
              <div class="text-base font-semibold text-slate-800 truncate">
                {{ w.title || unitTitleOf(w.unit_id) }}
              </div>
              <div class="text-xs text-slate-500 mt-1">
                {{ unitCodeOf(w.unit_id) }} · {{ formatDate(w.submitted_at) }}
              </div>
            </div>
            <el-tag :type="statusType(w.status)" size="small">{{ statusLabel(w.status) }}</el-tag>
          </div>

          <div v-if="w.image_path" class="mt-3">
            <img :src="w.image_path" alt="" class="w-full h-32 object-cover rounded" />
          </div>
          <div v-else-if="w.content" class="mt-3 text-sm text-slate-700 line-clamp-4 whitespace-pre-wrap">
            {{ w.content }}
          </div>
          <div v-else class="mt-3 text-xs text-slate-400 italic">（无内容）</div>

          <div
            v-if="w.ai_score != null || w.parent_comment || w.teacher_comment"
            class="mt-3 pt-3 border-t border-slate-100 space-y-1.5"
          >
            <div v-if="w.ai_score != null" class="flex items-center justify-between text-xs">
              <span class="text-slate-500">🤖 AI 评分</span>
              <span class="font-bold text-brand-600">{{ w.ai_score }} / 100</span>
            </div>
            <div v-if="w.ai_comment" class="text-xs text-slate-600">{{ w.ai_comment }}</div>
            <div v-if="w.parent_comment" class="text-xs text-green-700">👨‍👩‍👧 家长：{{ w.parent_comment }}</div>
            <div v-if="w.teacher_comment" class="text-xs text-blue-700">👩‍🏫 老师：{{ w.teacher_comment }}</div>
          </div>

          <div class="mt-4 flex gap-2">
            <el-button size="small" @click="openReview(w)">{{ w.parent_comment ? "改点评" : "家长点评" }}</el-button>
            <el-button size="small" type="danger" @click="remove(w)">删除</el-button>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 提交作品弹窗 -->
    <el-dialog v-model="showSubmitDialog" title="提交作品" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="单元" required>
          <el-select v-model="form.unit_id" class="!w-full" filterable>
            <el-option
              v-for="u in units"
              :key="u.id"
              :label="`${u.code} ${u.title_en} (${u.project_type || '无 Big Task'})`"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="如：Unit 5 我最喜欢的地方" />
        </el-form-item>
        <el-form-item label="类型" required>
          <el-radio-group v-model="form.work_type">
            <el-radio value="text">📝 文字</el-radio>
            <el-radio value="image">🖼️ 图片</el-radio>
            <el-radio value="drawing">🎨 画作</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="内容（文字）">
          <el-input v-model="form.content" type="textarea" :rows="4" placeholder="写作业、诗、profile 等" />
        </el-form-item>
        <el-form-item label="上传图片">
          <input ref="fileInputRef" type="file" accept="image/*" class="hidden" @change="onFileChange" />
          <el-button @click="$refs.fileInputRef.click()">选择图片</el-button>
          <span v-if="form._file" class="ml-2 text-xs text-slate-500">已选：{{ form._file.name }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSubmitDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">提交</el-button>
      </template>
    </el-dialog>

    <!-- 点评弹窗 -->
    <el-dialog v-model="showReviewDialog" title="家长 / 老师点评" width="500px">
      <el-form :model="reviewForm" label-width="100px">
        <el-form-item label="家长点评">
          <el-input v-model="reviewForm.parent_comment" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="老师点评">
          <el-input v-model="reviewForm.teacher_comment" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="reviewForm.status">
            <el-radio value="submitted">已提交</el-radio>
            <el-radio value="reviewed">已点评</el-radio>
            <el-radio value="approved">已通过</el-radio>
            <el-radio value="needs_revision">待修改</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReviewDialog = false">取消</el-button>
        <el-button type="primary" @click="saveReview">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, reactive } from "vue"
import { useRoute } from "vue-router"
import { ElMessage, ElMessageBox } from "element-plus"
import { useChildStore } from "@/stores/child"
import { textbookAPI, projectWorksAPI } from "@/api"

const route = useRoute()
const childStore = useChildStore()
let reloadTimer = null

const loading = ref(false)
const works = ref([])
const units = ref([])
const filterUnitId = ref(null)
const filterStatus = ref(null)
const showSubmitDialog = ref(false)
const showReviewDialog = ref(false)
const reviewingWork = ref(null)

const form = reactive({
  unit_id: null,
  title: "",
  work_type: "text",
  content: "",
  image_path: "",
  _file: null, // 暂存待上传的文件
})

const reviewForm = reactive({
  parent_comment: "",
  teacher_comment: "",
  status: "reviewed",
})

function statusLabel(s) {
  return { submitted: "已提交", reviewed: "已点评", approved: "已通过", needs_revision: "待修改" }[s] || s
}
function statusType(s) {
  return { submitted: "info", reviewed: "warning", approved: "success", needs_revision: "danger" }[s] || "info"
}
function unitTitleOf(uid) {
  const u = units.value.find((x) => x.id === uid)
  return u ? `${u.code} ${u.title_en}` : "(未知单元)"
}
function unitCodeOf(uid) {
  const u = units.value.find((x) => x.id === uid)
  return u ? u.code : ""
}
function formatDate(s) {
  if (!s) return ""
  return new Date(s).toLocaleString("zh-CN", { hour12: false })
}

async function loadUnits() {
  try {
    const versions = await textbookAPI.listVersions({ is_active: true })
    const englishVersions = versions.filter((v) => v.subject === "英语")
    const all = []
    for (const v of englishVersions) {
      const us = await textbookAPI.listUnits(v.id)
      all.push(...us)
    }
    units.value = all
  } catch (e) {
    ElMessage.error("教材单元加载失败")
  }
}

async function reload() {
  const childId = childStore.current?.id
  if (!childId) return
  loading.value = true
  try {
    const params = { child_id: childId }
    if (filterUnitId.value) params.unit_id = filterUnitId.value
    if (filterStatus.value) params.status = filterStatus.value
    works.value = await projectWorksAPI.list(params)
  } catch (e) {
    ElMessage.error("作品加载失败")
  } finally {
    loading.value = false
  }
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (file) {
    form._file = file
    form.image_path = file.name
  }
}

async function submit() {
  const childId = childStore.current?.id
  if (!childId) {
    ElMessage.warning("请先选择孩子")
    return
  }
  if (!form.unit_id) {
    ElMessage.warning("请选择教材单元")
    return
  }
  try {
    const created = await projectWorksAPI.submit({
      child_id: childId,
      unit_id: form.unit_id,
      work_type: form.work_type,
      title: form.title || undefined,
      content: form.content || undefined,
    })
    if (form._file) {
      await projectWorksAPI.uploadImage(created.id, form._file)
    }
    ElMessage.success("提交成功")
    showSubmitDialog.value = false
    Object.assign(form, { unit_id: null, title: "", work_type: "text", content: "", image_path: "", _file: null })
    reload()
  } catch (e) {
    ElMessage.error("提交失败")
  }
}

function openReview(w) {
  reviewingWork.value = w
  reviewForm.parent_comment = w.parent_comment || ""
  reviewForm.teacher_comment = w.teacher_comment || ""
  reviewForm.status = w.status === "submitted" ? "reviewed" : w.status
  showReviewDialog.value = true
}

async function saveReview() {
  if (!reviewingWork.value) return
  try {
    await projectWorksAPI.review(reviewingWork.value.id, {
      parent_comment: reviewForm.parent_comment || undefined,
      teacher_comment: reviewForm.teacher_comment || undefined,
      status: reviewForm.status,
    })
    ElMessage.success("已保存点评")
    showReviewDialog.value = false
    reload()
  } catch (e) {
    ElMessage.error("保存失败")
  }
}

async function remove(w) {
  try {
    await ElMessageBox.confirm("确定删除该作品？", "确认删除", { type: "warning" })
    await projectWorksAPI.remove(w.id)
    ElMessage.success("已删除")
    reload()
  } catch {
    // 用户取消 ElMessageBox 确认（不报错）
  }
}

onMounted(async () => {
  await loadUnits()
  const presetUnitId = Number(route.query.unit_id)
  if (presetUnitId) filterUnitId.value = presetUnitId
  reloadTimer = setTimeout(() => reload(), 200)
})

onUnmounted(() => {
  if (reloadTimer) clearTimeout(reloadTimer)
})
</script>

<style scoped>
.hidden {
  display: none;
}
</style>
