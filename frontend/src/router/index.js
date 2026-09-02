import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  // ==== 公开路由（无需认证） ====
  { path: "/login", name: "login", component: () => import("@/views/Login.vue"), meta: { title: "登录", public: true } },
  { path: "/setup", name: "setup", component: () => import("@/views/Setup.vue"), meta: { title: "首次启动", public: true } },

  // ==== 家长路由 ====
  { path: "/", redirect: "/dashboard" },
  { path: "/dashboard", name: "dashboard", component: () => import("@/views/Dashboard.vue"), meta: { title: "家长看板", role: "parent" } },
  { path: "/children", name: "children", component: () => import("@/views/Children.vue"), meta: { title: "孩子档案", role: "parent" } },
  { path: "/exams", name: "exams", component: () => import("@/views/Exams.vue"), meta: { title: "考试管理", role: "parent" } },
  { path: "/exam-analysis", name: "exam-analysis", component: () => import("@/views/ExamAnalysis.vue"), meta: { title: "考试分析", role: "parent" } },
  { path: "/homeworks", name: "homeworks", component: () => import("@/views/Homework.vue"), meta: { title: "作业追踪", role: "parent" } },
  { path: "/ai-reports", name: "ai-reports", component: () => import("@/views/AIReports.vue"), meta: { title: "AI 报告管理", role: "parent" } },
  { path: "/timeline", name: "timeline", component: () => import("@/views/Timeline.vue"), meta: { title: "成长时间轴", role: ["parent", "child"] } },
  { path: "/settings", name: "settings", component: () => import("@/views/Settings.vue"), meta: { title: "系统设置", role: "parent" } },
  { path: "/knowledge-points", name: "knowledge-points", component: () => import("@/views/KnowledgePoints.vue"), meta: { title: "知识点标签库", role: "parent" } },
  { path: "/wrong-questions", name: "wrong-questions", component: () => import("@/views/WrongQuestions.vue"), meta: { title: "错题本" } },
  { path: "/growth", name: "growth", component: () => import("@/views/Growth.vue"), meta: { title: "生长发育", role: ["parent", "child"] } },
  { path: "/social-emotional", name: "social-emotional", component: () => import("@/views/SocialEmotional.vue"), meta: { title: "社交情感", role: "parent" } },
  { path: "/interests", name: "interests", component: () => import("@/views/Interests.vue"), meta: { title: "兴趣特长", role: "parent" } },
  { path: "/rewards", name: "rewards", component: () => import("@/views/Rewards.vue"), meta: { title: "奖励商城" } },
  { path: "/achievements", name: "achievements", component: () => import("@/views/Achievements.vue"), meta: { title: "成就墙" } },
  { path: "/question-banks", name: "question-banks", component: () => import("@/views/QuestionBank.vue"), meta: { title: "题库练习" } },
  { path: "/exercise", name: "exercise", component: () => import("@/views/Exercise.vue"), meta: { title: "开始练习" } },
  { path: "/study-progress", name: "study-progress", component: () => import("@/views/StudyProgress.vue"), meta: { title: "教材学习进度" } },
  { path: "/project-works", name: "project-works", component: () => import("@/views/ProjectWorks.vue"), meta: { title: "单元 Big Task" } },
  { path: "/about", name: "about", component: () => import("@/views/About.vue"), meta: { title: "关于系统"} },

  // ==== 孩子路由 ====
  { path: "/child", component: () => import("@/views/ChildDashboard.vue"), meta: { title: "我的看板", role: "child" } },

  // ==== 404 ====
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  // 1) 公开路由：login / setup，直接放行
  if (to.meta.public) return true;

  // 2) 未登录：先检查是否需要 setup，否则跳登录
  if (!auth.isAuthenticated) {
    try {
      const needsSetup = await auth.checkSetup();
      if (needsSetup) return { path: "/setup", query: { redirect: to.fullPath } };
    } catch (e) {
      // 后端连不上：让用户至少能看到登录页
      console.warn("setup-status check failed:", e);
    }
    return { path: "/login", query: { redirect: to.fullPath } };
  }

  // 2.5) 已登录但本次会话尚未校验过 token 有效性（覆盖密钥轮换 / token 过期场景）：
  // 先用 /auth/me 校验，失效则 refreshMe 内部会清 token 并登出，这里直接干净跳登录，
  // 避免带失效 token 把受保护页面渲染出来、再在 mounted 里刷出一堆 401。
  if (!auth.tokenValidated) {
    await auth.refreshMe();
    if (!auth.isAuthenticated) {
      return { path: "/login", query: { redirect: to.fullPath } };
    }
  }

  // 3) 已登录但角色不匹配：跳到对应首页
  if (to.meta.role) {
    const allowed = Array.isArray(to.meta.role) ? to.meta.role : [to.meta.role];
    if (!allowed.includes(auth.user.role)) {
      return auth.isChild ? "/child" : "/";
    }
  }

  return true;
});

router.afterEach((to) => {
  document.title = `${to.meta.title || ""} - 学业成长系统`;
});

export default router;
