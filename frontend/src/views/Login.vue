<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="text-2xl font-bold mb-1">学业成长系统</h2>
      <p class="text-sm text-gray-500 mb-6">家长 / 孩子账号登录</p>
      <el-form :model="form" @keyup.enter="submit" label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="家长或孩子用户名" autofocus />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="6 位以上" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="w-full" @click="submit">登录</el-button>
      </el-form>
      <p v-if="errMsg" class="text-red-500 text-sm mt-3">{{ errMsg }}</p>
      <!-- 局域网访问提示 -->
      <div class="mt-4 p-3 bg-slate-50 rounded-lg text-xs text-slate-500 leading-relaxed">
        <div class="font-medium text-slate-700 mb-1">📱 局域网访问</div>
        <div v-if="lanUrl">
          其他设备请访问：<span class="font-mono text-brand-600 break-all">{{ lanUrl }}</span>
        </div>
        <div v-else class="text-slate-400">正在获取服务器地址...</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useChildStore } from "@/stores/child";
import { configAPI } from "@/api";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const childStore = useChildStore();

const form = reactive({ username: "", password: "" });
const loading = ref(false);
const errMsg = ref("");
const lanUrl = ref("");

async function loadLanUrl() {
  try {
    const cfg = await configAPI.getPublicConfig();
    lanUrl.value = cfg.lan_url || "";
  } catch {
    lanUrl.value = "";
  }
}

async function submit() {
  if (!form.username || !form.password) {
    errMsg.value = "用户名和密码不能为空";
    return;
  }
  loading.value = true;
  errMsg.value = "";
  try {
    const user = await auth.login(form.username, form.password);
    if (user.role === "parent") {
      try {
        await childStore.loadChildren();
      } catch (e) {
        console.warn("加载孩子列表失败：", e);
      }
    } else if (user.role === "child") {
      childStore.bootstrapChild({ id: user.child_id, name: user.display_name });
    }
    const next = route.query.redirect || (user.role === "child" ? "/child" : "/");
    router.push(next);
  } catch (e) {
    errMsg.value = e.response?.data?.detail || "登录失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadLanUrl();
});
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card {
  background: white;
  padding: 2.5rem;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  width: 100%;
  max-width: 380px;
}
</style>