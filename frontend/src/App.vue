<script setup>
import { computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useChildStore } from "@/stores/child";
import { useAuthStore } from "@/stores/auth";
import { ElConfigProvider } from "element-plus";
// element-plus 按需引入后,locale 由 el-config-provider 传递
// (原先靠 app.use(ElementPlus, { locale }) 全量注册时传入)
import zhCn from "element-plus/dist/locale/zh-cn.mjs";
import Layout from "@/components/Layout.vue";

const route = useRoute();
const childStore = useChildStore();
const auth = useAuthStore();

const useLayout = computed(() => auth.isAuthenticated && !route.meta.public);

onMounted(async () => {
  await childStore.loadConfig();
  // 只在已认证后才初始化孩子上下文（认证页面 / setup 不需要）
  if (auth.isAuthenticated) {
    if (auth.isChild) {
      // 孩子账号后端禁止 /api/children，用已从 localStorage 恢复的用户信息自举，
      // 覆盖刷新页面后 childStore 仍为空的场景
      childStore.bootstrapChild({
        id: auth.currentChildId,
        name: auth.user?.display_name,
      });
    } else {
      try {
        await childStore.loadChildren();
      } catch (e) {
        console.warn("加载孩子列表失败：", e);
      }
    }
  }
});
</script>

<template>
  <el-config-provider :locale="zhCn">
    <Layout v-if="useLayout">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <div class="route-wrapper">
            <component :is="Component" />
          </div>
        </transition>
      </router-view>
    </Layout>
    <router-view v-else v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </el-config-provider>
</template>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
