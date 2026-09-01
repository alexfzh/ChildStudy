<template>
  <div class="setup-page">
    <div class="setup-card">
      <h2 class="text-2xl font-bold mb-1">🎉 欢迎使用学业成长系统</h2>
      <p class="text-sm text-gray-500 mb-6">首次启动，请创建第一个家长账号</p>

      <el-form :model="form" label-position="top">
        <el-form-item label="家庭名称">
          <el-input v-model="form.family_name" />
        </el-form-item>
        <el-form-item label="用户名（用于登录）">
          <el-input v-model="form.username" placeholder="如 dad / mom / 爸爸" autofocus />
        </el-form-item>
        <el-form-item label="显示名（系统里显示的中文名）">
          <el-input v-model="form.display_name" placeholder="如 爸爸 / 妈妈" />
        </el-form-item>
        <el-form-item label="密码（6 位以上）">
          <el-input v-model="form.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.password_confirm" type="password" show-password />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="w-full" @click="submit">
          创建家长账号并进入
        </el-button>
      </el-form>
      <p v-if="errMsg" class="text-red-500 text-sm mt-3 whitespace-pre-line">{{ errMsg }}</p>

      <div class="mt-6 p-4 bg-blue-50 rounded text-xs text-gray-600 leading-relaxed">
        <p class="font-medium mb-1">📌 关于初始数据</p>
        <p>
          如果你从老版本（v1.5.x）升级上来，<b>已有的孩子档案会自动保留</b>（绑定到刚创建的家庭下）。
          登录后可以进入「系统设置 → 账号管理」为每个孩子创建登录账号。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useChildStore } from "@/stores/child";

const router = useRouter();
const auth = useAuthStore();
const childStore = useChildStore();

const form = reactive({
  family_name: "我的家",
  username: "",
  display_name: "",
  password: "",
  password_confirm: "",
});
const loading = ref(false);
const errMsg = ref("");

async function submit() {
  errMsg.value = "";
  if (!form.username || !form.password || !form.display_name) {
    errMsg.value = "请填写完整信息";
    return;
  }
  if (form.password.length < 6) {
    errMsg.value = "密码至少 6 位";
    return;
  }
  if (form.password !== form.password_confirm) {
    errMsg.value = "两次输入的密码不一致";
    return;
  }
  loading.value = true;
  try {
    await auth.setup({
      familyName: form.family_name,
      username: form.username,
      password: form.password,
      displayName: form.display_name,
    });
    // 登录后立刻加载孩子列表
    try {
      await childStore.loadChildren();
    } catch (e) {
      console.warn("加载孩子列表失败：", e);
    }
    router.push("/");
  } catch (e) {
    errMsg.value = e.response?.data?.detail || "创建失败";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.setup-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}
.setup-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 460px;
}
</style>