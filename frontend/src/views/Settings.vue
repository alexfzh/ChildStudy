<script setup>
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { dashboardAPI, authAPI } from "@/api";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const compareData = ref(null);

const loadCompare = async () => {
  try {
    compareData.value = await dashboardAPI.compare();
  } catch (e) {
    /* noop */
  }
};

// ===== 修改密码 =====
const formRef = ref(null);
const submitting = ref(false);
const form = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const validateConfirm = (rule, value, callback) => {
  if (value !== form.new_password) {
    callback(new Error("两次输入的新密码不一致"));
  } else {
    callback();
  }
};

const rules = {
  old_password: [{ required: true, message: "请输入原密码", trigger: "blur" }],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, max: 128, message: "密码长度 6-128 位", trigger: "blur" },
  ],
  confirm_password: [
    { required: true, message: "请再次输入新密码", trigger: "blur" },
    { validator: validateConfirm, trigger: "blur" },
  ],
};

const handleChangePassword = async () => {
  if (!formRef.value) return;
  try {
    await formRef.value.validate();
  } catch {
    return;
  }
  submitting.value = true;
  try {
    const r = await authAPI.changePassword({
      old_password: form.old_password,
      new_password: form.new_password,
    });
    ElMessage.success(r.msg || "密码修改成功");
    form.old_password = "";
    form.new_password = "";
    form.confirm_password = "";
    formRef.value.resetFields();
  } catch (e) {
    // 401（原密码错误）等错误由拦截器统一弹错
  } finally {
    submitting.value = false;
  }
};

onMounted(loadCompare);
</script>

<template>
  <div class="space-y-5">
    <!-- 当前账号 -->
    <div class="card p-5">
      <h3 class="font-semibold text-slate-800 mb-3">当前账号</h3>
      <div class="flex items-center gap-3">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center text-white font-medium"
          :style="{ background: auth.user?.avatar_color || '#6366f1' }"
        >
          {{ (auth.user?.display_name || '?').charAt(0) }}
        </div>
        <div>
          <div class="font-medium text-slate-800">{{ auth.user?.display_name }}</div>
          <div class="text-xs text-slate-500">
            用户名：{{ auth.user?.username }} · {{ auth.user?.role === 'parent' ? '家长' : '孩子' }}
          </div>
        </div>
      </div>
    </div>

    <!-- 修改密码 -->
    <div class="card p-5">
      <h3 class="font-semibold text-slate-800 mb-1">修改密码</h3>
      <p class="text-sm text-slate-500 mb-4">需要输入原密码以确认身份</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="96px"
        class="max-w-md"
        @submit.prevent
      >
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="form.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="form.new_password" type="password" show-password placeholder="6-128 位" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="form.confirm_password" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="submitting" @click="handleChangePassword">保存修改</el-button>
        </el-form-item>
      </el-form>
    </div>

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
