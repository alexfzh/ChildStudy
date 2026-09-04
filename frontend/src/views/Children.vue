<script setup>
import { ref, onMounted } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import dayjs from "dayjs"
import { useChildStore } from "@/stores/child"
import { dashboardAPI } from "@/api"
import SubjectPicker from "@/components/SubjectPicker.vue"

const childStore = useChildStore()

// 多孩子对比数据（多孩子家庭展示各自的优势与需关注领域）
const compareData = ref(null)
const loadCompare = async () => {
  try {
    compareData.value = await dashboardAPI.compare()
  } catch (e) {
    /* noop */
  }
}
onMounted(loadCompare)

const dialogVisible = ref(false)
const editing = ref(null)

const blank = () => ({
  name: "",
  grade: "",
  school: "",
  avatar_color: "#6366f1",
  birth_date: null,
  gender: null,
  notes: "",
  subjects: ["语文", "数学", "英语"],
})

const form = ref(blank())

// 升年级弹窗
const promoteDialogVisible = ref(false)
const promoteForm = ref({ grade: "", effective_from: dayjs().format("YYYY-MM-DD"), note: "" })
const promotingChild = ref(null)

// 历史展开状态
const expandedHistory = ref(new Set())

const openCreate = () => {
  editing.value = null
  form.value = blank()
  dialogVisible.value = true
}

const openEdit = (child) => {
  editing.value = child
  form.value = { ...blank(), ...child, subjects: [...(child.subjects || [])] }
  dialogVisible.value = true
}

const submit = async () => {
  if (!form.value.name || !form.value.grade) {
    ElMessage.warning("请填写姓名和年级")
    return
  }
  try {
    if (editing.value) {
      await childStore.update(editing.value.id, form.value)
      ElMessage.success("已保存")
    } else {
      await childStore.create(form.value)
      ElMessage.success("已添加孩子档案")
    }
    dialogVisible.value = false
  } catch (e) {
    /* axios 已提示 */
  }
}

const remove = async (child) => {
  await ElMessageBox.confirm(`确认删除「${child.name}」及其所有数据吗？此操作不可恢复。`, "删除确认", {
    type: "warning",
    confirmButtonText: "删除",
    cancelButtonText: "取消",
  })
  await childStore.remove(child.id)
  ElMessage.success("已删除")
}

// 升年级
const openPromote = (child) => {
  promotingChild.value = child
  promoteForm.value = {
    grade: "",
    effective_from: dayjs().format("YYYY-MM-DD"),
    note: "",
  }
  promoteDialogVisible.value = true
}

const submitPromote = async () => {
  const f = promoteForm.value
  if (!f.grade.trim()) {
    ElMessage.warning("请填写新年级")
    return
  }
  if (!f.effective_from) {
    ElMessage.warning("请选择生效日期")
    return
  }
  try {
    await childStore.addGradeHistory(promotingChild.value.id, {
      grade: f.grade.trim(),
      effective_from: f.effective_from,
      note: f.note.trim() || null,
    })
    ElMessage.success("已升年级，时间轴已自动留痕")
    promoteDialogVisible.value = false
  } catch (e) {
    /* axios */
  }
}

// 删除某条历史
const removeHistory = async (child, historyId) => {
  try {
    await ElMessageBox.confirm("确认删除这条年级历史？", "删除", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    })
    await childStore.removeGradeHistory(child.id, historyId)
    ElMessage.success("已删除")
  } catch (e) {
    /* user cancel */
  }
}

// 展开/收起历史
const toggleHistory = (childId) => {
  if (expandedHistory.value.has(childId)) {
    expandedHistory.value.delete(childId)
  } else {
    expandedHistory.value.add(childId)
  }
}

const colorOptions = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"]

// 计算每个 child 的历史
const historyOf = (childId) => childStore.gradeHistoryMap[childId] || []
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-lg font-semibold text-slate-800">孩子档案</h2>
        <p class="text-sm text-slate-500 mt-0.5">
          最多支持 {{ childStore.maxChildren }} 个孩子，可一键切换。每个孩子的升年级会留痕到时间轴
        </p>
      </div>
      <button class="btn-primary" :disabled="!childStore.canAddMore" @click="openCreate">+ 添加孩子</button>
    </div>

    <div v-if="childStore.children.length === 0" class="card p-10 text-center">
      <div class="text-5xl mb-3">👶</div>
      <div class="text-slate-700 font-medium mb-1">还没有孩子档案</div>
      <div class="text-sm text-slate-500 mb-5">点击右上角添加</div>
      <button class="btn-primary" @click="openCreate">+ 添加第一个孩子</button>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="c in childStore.children"
        :key="c.id"
        class="card p-5"
        :class="{ 'ring-2 ring-brand-500': childStore.currentId === c.id }"
      >
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-3">
            <div
              class="w-12 h-12 rounded-full flex items-center justify-center text-white text-xl font-medium"
              :style="{ backgroundColor: c.avatar_color }"
            >
              {{ c.name.charAt(0) }}
            </div>
            <div>
              <div class="font-semibold text-slate-800">{{ c.name }}</div>
              <div class="text-sm text-slate-500 mt-0.5">
                当前：<span class="font-medium text-brand-600">{{ c.grade }}</span>
                <span v-if="c.school"> · {{ c.school }}</span>
              </div>
            </div>
          </div>
          <span v-if="childStore.currentId === c.id" class="badge-info">当前选中</span>
        </div>

        <div v-if="c.subjects?.length" class="flex flex-wrap gap-1.5 mt-3">
          <span v-for="s in c.subjects" :key="s" class="badge bg-slate-100 text-slate-600">{{ s }}</span>
        </div>

        <div v-if="c.notes" class="text-xs text-slate-500 mt-3 leading-relaxed">{{ c.notes }}</div>

        <!-- 年级历史 -->
        <div v-if="historyOf(c.id).length > 0" class="mt-4 pt-3 border-t border-slate-100">
          <button
            class="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 mb-2"
            @click="toggleHistory(c.id)"
          >
            <span>{{ expandedHistory.has(c.id) ? "▼" : "▶" }}</span>
            <span>年级历史（{{ historyOf(c.id).length }} 次）</span>
          </button>
          <div v-if="expandedHistory.has(c.id)" class="space-y-1.5 text-xs">
            <div
              v-for="h in historyOf(c.id)"
              :key="h.id"
              class="flex items-center justify-between py-1.5 px-2 rounded bg-slate-50 hover:bg-slate-100 group"
            >
              <div>
                <span class="font-medium text-slate-700">{{ h.grade }}</span>
                <span class="text-slate-400 ml-2">{{ dayjs(h.effective_from).format("YYYY-MM-DD") }}</span>
                <span v-if="h.note" class="text-slate-500 ml-2">· {{ h.note }}</span>
              </div>
              <button
                class="text-slate-300 hover:text-rose-500 opacity-0 group-hover:opacity-100"
                title="删除该条历史"
                @click="removeHistory(c, h.id)"
              >
                🗑
              </button>
            </div>
          </div>
        </div>

        <div class="flex gap-2 mt-4">
          <button
            v-if="childStore.currentId !== c.id"
            class="btn-secondary flex-1"
            @click="childStore.setCurrent(c.id)"
          >
            切换到此孩子
          </button>
          <button class="btn-primary flex-1" @click="openPromote(c)">🎓 升年级</button>
          <button class="btn-ghost" @click="openEdit(c)">编辑</button>
          <button class="btn-danger" @click="remove(c)">删除</button>
        </div>
      </div>
    </div>

    <!-- 多孩子对比（家长视角：各自优势与需关注领域） -->
    <div v-if="compareData && compareData.children.length > 1" class="card p-5 mt-4">
      <h3 class="font-semibold text-slate-800 mb-1">多孩子对比</h3>
      <p class="text-sm text-slate-500 mb-4">非排名导向，呈现各自的优势与需要关注的领域</p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div v-for="c in compareData.children" :key="c.id" class="p-4 rounded-xl border border-slate-200">
          <div class="flex items-center gap-2 mb-3">
            <div
              class="w-9 h-9 rounded-full flex items-center justify-center text-white font-medium"
              :style="{ backgroundColor: c.avatar_color }"
            >
              {{ c.name.charAt(0) }}
            </div>
            <div>
              <div class="font-medium text-slate-800">{{ c.name }}</div>
              <div class="text-xs text-slate-500">{{ c.grade }} · {{ c.total_exams }} 次考试</div>
            </div>
          </div>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-slate-500">平均分</span><span class="font-medium">{{ c.average_score }}%</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">最强科目</span
              ><span class="font-medium text-emerald-600">{{ c.best_subject || "—" }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">需要关注</span
              ><span class="font-medium text-amber-600">{{ c.needs_attention_subject || "—" }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 新增/编辑 -->
    <el-dialog v-model="dialogVisible" :title="editing ? '编辑档案' : '添加孩子'" width="500px">
      <el-form label-position="top">
        <el-form-item label="姓名" required>
          <el-input v-model="form.name" placeholder="如：小米" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="form.grade" placeholder="如：三年级 / 初二" />
          <div class="text-xs text-slate-400 mt-1">💡 修改年级请用下方「升年级」按钮（会留痕到时间轴）</div>
        </el-form-item>
        <el-form-item label="学校">
          <el-input v-model="form.school" placeholder="选填" />
        </el-form-item>
        <el-form-item label="头像颜色">
          <div class="flex gap-2">
            <button
              v-for="color in colorOptions"
              :key="color"
              type="button"
              class="w-8 h-8 rounded-full transition border-2"
              :class="form.avatar_color === color ? 'border-slate-800 scale-110' : 'border-transparent'"
              :style="{ backgroundColor: color }"
              @click="form.avatar_color = color"
            />
          </div>
        </el-form-item>
        <el-form-item label="关注科目">
          <SubjectPicker v-model="form.subjects" />
          <div class="text-xs text-slate-400 mt-2">
            💡 点选预设科目，或「+ 自定义」添加（如历史、化学）。录考试时只能从这些科目里选
          </div>
        </el-form-item>
        <el-form-item label="出生日期">
          <el-date-picker
            v-model="form.birth_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择孩子的出生日期"
            class="w-full"
          />
          <div class="text-xs text-slate-400 mt-1">💡 用于身高、体重、BMI 生长曲线查表与年龄计算</div>
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio-button :value="null">未填</el-radio-button>
            <el-radio-button value="male">男</el-radio-button>
            <el-radio-button value="female">女</el-radio-button>
          </el-radio-group>
          <div class="text-xs text-slate-400 mt-1">用于 BMI / 身高生长曲线查表（如未填，BMI 按男孩参考）</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="如：性格特点、特长" />
        </el-form-item>
      </el-form>
      <template #footer>
        <button class="btn-ghost" @click="dialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submit">保存</button>
      </template>
    </el-dialog>

    <!-- 升年级 -->
    <el-dialog v-model="promoteDialogVisible" title="升年级" width="480px">
      <div v-if="promotingChild" class="space-y-3">
        <div class="text-sm text-slate-600">
          当前孩子：<span class="font-medium">{{ promotingChild.name }}</span> （当前年级：<span
            class="font-medium text-brand-600"
            >{{ promotingChild.grade }}</span
          >）
        </div>
        <el-form label-position="top">
          <el-form-item label="新年级" required>
            <el-input v-model="promoteForm.grade" placeholder="如：四年级 / 初二" maxlength="32" />
          </el-form-item>
          <el-form-item label="生效日期" required>
            <el-date-picker v-model="promoteForm.effective_from" type="date" value-format="YYYY-MM-DD" class="w-full" />
          </el-form-item>
          <el-form-item label="备注（可选）">
            <el-input
              v-model="promoteForm.note"
              type="textarea"
              :rows="2"
              placeholder="如：暑假后升入四年级"
              maxlength="256"
            />
          </el-form-item>
        </el-form>
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 leading-relaxed">
          💡 升年级会：
          <ul class="list-disc list-inside mt-1 space-y-0.5">
            <li>写入年级历史（可随时回看或删除）</li>
            <li>自动同步到孩子的「成长时间轴」</li>
            <li>历史考试/作业的 grade 快照不受影响（已记录当时的年级）</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <button class="btn-ghost" @click="promoteDialogVisible = false">取消</button>
        <button class="btn-primary ml-2" @click="submitPromote">确认升年级</button>
      </template>
    </el-dialog>
  </div>
</template>
