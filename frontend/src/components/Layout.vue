<script setup>
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useChildStore } from "@/stores/child";
import { useAuthStore } from "@/stores/auth";
import { ElMessageBox } from "element-plus";
import ChildSelector from "./ChildSelector.vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const childStore = useChildStore();
const sidebarOpen = ref(false);

const avatarChar = computed(() => {
  const name = auth.user?.display_name || "";
  return name ? name.charAt(0) : "?";
});

async function handleLogout() {
  try {
    await ElMessageBox.confirm("确定要退出登录吗？", "确认", { type: "warning" });
  } catch {
    return; // 用户取消
  }
  auth.logout();
  router.push("/login");
}

const navGroups = [
  {
    label: "概览",
    items: [
      { name: "dashboard", path: "/dashboard", label: "家长看板", icon: "📊", roles: ["parent"] },
      { name: "child-dashboard", path: "/child", label: "我的看板", icon: "🌟", roles: ["child"] },
      { name: "children", path: "/children", label: "孩子档案", icon: "👶", roles: ["parent"] },
    ],
  },
  {
    label: "学业",
    items: [
      { name: "exams", path: "/exams", label: "考试管理", icon: "📝", roles: ["parent"] },
      { name: "homeworks", path: "/homeworks", label: "作业追踪", icon: "📚", roles: ["parent"] },
      { name: "knowledge-points", path: "/knowledge-points", label: "知识点标签库", icon: "🏷️", roles: ["parent"] },
      { name: "wrong-questions", path: "/wrong-questions", label: "错题本", icon: "📙", roles: ["parent", "child"] },
      { name: "question-banks", path: "/question-banks", label: "题库练习", icon: "✏️", roles: ["parent", "child"] },
      { name: "study-progress", path: "/study-progress", label: "教材学习进度", icon: "📚", roles: ["parent", "child"] },
      { name: "ai-reports", path: "/ai-reports", label: "AI 报告管理", icon: "🤖", roles: ["parent"] },
    ],
  },
  {
    label: "激励",
    items: [
      { name: "rewards", path: "/rewards", label: "奖励商城", icon: "🎁", roles: ["parent", "child"] },
      { name: "achievements", path: "/achievements", label: "成就墙", icon: "🏆", roles: ["parent", "child"] },
    ],
  },
  {
    label: "成长",
    items: [
      { name: "timeline", path: "/timeline", label: "成长时间轴", icon: "🌱", roles: ["parent", "child"] },
      { name: "project-works", path: "/project-works", label: "Big Task 作品", icon: "🎨", roles: ["parent", "child"] },
      { name: "growth", path: "/growth", label: "生长发育", icon: "📏", roles: ["parent", "child"] },
      { name: "social-emotional", path: "/social-emotional", label: "社交情感", icon: "💭", roles: ["parent"] },
      { name: "interests", path: "/interests", label: "兴趣特长", icon: "🎨", roles: ["parent"] },
    ],
  },
  {
    label: "系统",
    items: [
      { name: "settings", path: "/settings", label: "系统设置", icon: "⚙️", roles: ["parent", "child"] },
      { name: "about", path: "/about", label: "关于系统", icon: "ℹ️", roles: ["parent", "child"] },
    ],
  },
];

// 按角色过滤菜单项：孩子只看白名单，家长看全部
const canSee = (item) => {
  const roles = item.roles || ["parent", "child"];
  return auth.isChild ? roles.includes("child") : roles.includes("parent");
};

// 分组菜单（概览/学业/激励/成长/系统）
const groupExpanded = ref(navGroups.map(() => true));

const toggleGroup = (idx) => {
  groupExpanded.value[idx] = !groupExpanded.value[idx];
};

const currentTitle = computed(() => route.meta.title || "");

const closeSidebar = () => {
  sidebarOpen.value = false;
};
</script>

<template>
  <div class="flex h-screen overflow-hidden">
    <!-- 移动端遮罩 -->
    <div
      v-if="sidebarOpen"
      class="fixed inset-0 bg-black/40 z-30 md:hidden"
      @click="closeSidebar"
    />

    <!-- 侧边栏 -->
    <aside
      :class="[
        'bg-white border-r border-slate-200 flex flex-col flex-shrink-0 transition-transform duration-200',
        'fixed md:relative inset-y-0 left-0 z-40 w-[260px]',
        sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      ]"
    >
      <!-- Logo -->
      <div class="px-5 py-5 border-b border-slate-100 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white text-lg shadow-sm">
            🌱
          </div>
          <div>
            <div class="font-semibold text-slate-800 leading-tight">学业成长</div>
            <div class="text-[11px] text-slate-400 leading-tight">学业数据 · 外部 AI</div>
          </div>
        </div>
        <!-- 移动端关闭按钮 -->
        <button class="md:hidden text-slate-400 hover:text-slate-600" @click="closeSidebar">✕</button>
      </div>

      <!-- 孩子选择器 -->
      <div class="px-3 py-3 border-b border-slate-100">
        <ChildSelector />
      </div>

      <!-- 导航 -->
      <nav class="flex-1 px-2 py-3 overflow-y-auto">
        <template v-for="(group, gIdx) in navGroups" :key="group.label">
          <!-- 分组标题（可点击折叠） -->
          <button
            v-if="group.items.filter(canSee).length"
            type="button"
            class="flex items-center justify-between w-full px-3 py-2.5 text-sm font-semibold text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer active:scale-[0.98]"
            @click="toggleGroup(gIdx)"
          >
            <span>{{ group.label }}</span>
            <span
              class="text-xs transition-transform duration-200"
              :class="groupExpanded[gIdx] ? 'rotate-180' : ''"
            >▾</span>
          </button>
          <!-- 菜单项 -->
          <div
            class="overflow-hidden transition-all duration-200 ease-out"
            :style="{ maxHeight: groupExpanded[gIdx] ? '600px' : '0px', opacity: groupExpanded[gIdx] ? 1 : 0 }"
          >
            <router-link
              v-for="item in group.items.filter(canSee)"
              :key="item.name"
              :to="item.path"
              class="flex items-center gap-3 px-3 py-2.5 mb-0.5 rounded-lg text-sm font-medium transition-all active:scale-[0.98]"
              :class="route.name === item.name ? 'bg-brand-50 text-brand-600' : 'text-slate-600 hover:bg-slate-50'"
              @click="closeSidebar"
            >
              <span class="text-base">{{ item.icon }}</span>
              <span class="flex-1">{{ item.label }}</span>
            </router-link>
          </div>
        </template>
      </nav>

      <!-- 底部提示 -->
      <div class="px-4 py-3 border-t border-slate-100 text-[11px] text-slate-400 leading-relaxed">
        💡 数据完全本地存储<br/>
        隐私优先 · 离线可用
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="flex-1 flex flex-col overflow-hidden w-full min-w-0">
      <!-- 顶栏 -->
      <header class="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 flex-shrink-0">
        <div class="flex items-center gap-3">
          <!-- 移动端菜单按钮 -->
          <button class="md:hidden text-slate-600 hover:text-slate-800 text-xl leading-none" @click="sidebarOpen = true">
            ☰
          </button>
          <div class="font-semibold text-slate-800">{{ currentTitle }}</div>
        </div>
        <div class="flex items-center gap-2">
          <el-dropdown trigger="click" @command="(c) => c === 'logout' && handleLogout()">
            <button class="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-slate-50 transition-colors">
              <span
                class="w-8 h-8 rounded-full flex items-center justify-center text-white font-medium shadow-sm"
                :style="{ background: auth.user?.avatar_color || '#6366f1' }"
              >{{ avatarChar }}</span>
              <span class="hidden md:inline text-sm text-slate-700">{{ auth.user?.display_name }}</span>
              <span class="hidden md:inline text-xs text-slate-400 ml-1">({{ auth.user?.role === 'parent' ? '家长' : '孩子' }})</span>
              <span class="text-slate-400 text-xs">▾</span>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  <span class="text-xs text-slate-500">{{ auth.user?.username }}</span>
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <span class="text-red-500">退出登录</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 内容区 -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-7xl mx-auto px-4 md:px-6 py-6">
          <slot />
        </div>
      </div>
    </main>
  </div>
</template>
