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
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useChildStore } from "@/stores/child";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const childStore = useChildStore();

const form = reactive({ username: "", password: "" });
const loading = ref(false);
const errMsg = ref("");

async function submit() {
  if (!form.username || !form.password) {
    errMsg.value = "用户名和密码不能为空";
    return;
  }
  loading.value = true;
  errMsg.value = "";
  try {
    const user = await auth.login(form.username, form.password);
    // 加载孩子列表（家长端需要）
    if (user.role === "parent") {
      try {
        await childStore.loadChildren();
      } catch (e) {
        // 容错：即使拉失败也不阻塞登录
        console.warn("加载孩子列表失败：", e);
      }
    }
    // 跳转到登录前想去的页面或首页
    const next = route.query.redirect || (user.role === "child" ? "/child" : "/");
    router.push(next);
  } catch (e) {
    errMsg.value = e.response?.data?.detail || "登录失败";
  } finally {
    loading.value = false;
  }
}
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