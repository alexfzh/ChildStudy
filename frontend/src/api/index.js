import axios from "axios";
import { ElMessage } from "element-plus";

const api = axios.create({
  baseURL: "/api",
  timeout: 90000,
});

// ==== Auth: Bearer token 拦截器 (v1.6.0) ====
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (err) => {
    // 401 = token 过期 / 无效 → 清本地 token + 跳登录
    if (err.response?.status === 401 && !err.config?.url?.includes("/auth/")) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      localStorage.removeItem("accessible_child_ids");
      // 避免重复弹错（router guard 会处理跳转）
      const cur = window.location.pathname;
      if (cur !== "/login" && cur !== "/setup") {
        window.location.href = "/login";
      }
      return Promise.reject(err);
    }
    const msg = err.response?.data?.detail || err.message || "请求失败";
    ElMessage.error(typeof msg === "string" ? msg : JSON.stringify(msg));
    return Promise.reject(err);
  }
);

export const authAPI = {
  setupStatus: () => api.get("/auth/setup-status").then((r) => r.data),
  setup: (data) => api.post("/auth/setup", data).then((r) => r.data),
  login: (data) => api.post("/auth/login", data).then((r) => r.data),
  logout: () => api.post("/auth/logout").then((r) => r.data),
  me: (token) =>
    api.get("/auth/me", { headers: token ? { Authorization: `Bearer ${token}` } : {} }).then((r) => r.data),
  listUsers: () => api.get("/auth/users").then((r) => r.data),
  createUser: (data) => api.post("/auth/users", data).then((r) => r.data),
  changePassword: (data) => api.post("/auth/change-password", data).then((r) => r.data),
};

export const childrenAPI = {
  list: () => api.get("/children").then((r) => r.data),
  create: (data) => api.post("/children", data).then((r) => r.data),
  update: (id, data) => api.put(`/children/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/children/${id}`).then((r) => r.data),
  listGradeHistory: (id) => api.get(`/children/${id}/grade-history`).then((r) => r.data),
  addGradeHistory: (id, data) => api.post(`/children/${id}/grade-history`, data).then((r) => r.data),
  removeGradeHistory: (id, historyId) => api.delete(`/children/${id}/grade-history/${historyId}`).then((r) => r.data),
};

export const examsAPI = {
  list: (params) => api.get("/exams", { params }).then((r) => r.data),
  create: (data) => api.post("/exams", data).then((r) => r.data),
  update: (id, data) => api.put(`/exams/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/exams/${id}`).then((r) => r.data),
  // 试卷纸面（AI 录入）
  submitPaper: (id, data) => api.post(`/exams/${id}/paper`, data).then((r) => r.data),
  listQuestions: (id) => api.get(`/exams/${id}/questions`).then((r) => r.data),
  clearPaper: (id) => api.delete(`/exams/${id}/paper`).then((r) => r.data),
  // 分析
  analyze: (id) => api.get(`/exams/${id}/analysis`).then((r) => r.data),
  paperAnalysis: (id) => api.get(`/exams/${id}/paper-analysis`).then((r) => r.data),
  historyAnalysis: (params) => api.get("/exams/analysis/history", { params }).then((r) => r.data),
};

export const homeworksAPI = {
  list: (params) => api.get("/homeworks", { params }).then((r) => r.data),
  create: (data) => api.post("/homeworks", data).then((r) => r.data),
  update: (id, data) => api.put(`/homeworks/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/homeworks/${id}`).then((r) => r.data),
};

export const timelineAPI = {
  list: (params) => api.get("/timeline", { params }).then((r) => r.data),
  create: (data) => api.post("/timeline", data).then((r) => r.data),
  update: (id, data) => api.put(`/timeline/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/timeline/${id}`).then((r) => r.data),
};

export const dashboardAPI = {
  get: (childId) => api.get(`/dashboard/${childId}`).then((r) => r.data),
  compare: () => api.get("/dashboard/compare/all").then((r) => r.data),
};

export const reportsAPI = {
  list: (childId) => api.get("/reports", { params: { child_id: childId } }).then((r) => r.data),
  get: (id) => api.get(`/reports/${id}`).then((r) => r.data),
  create: (data) => api.post("/reports", data).then((r) => r.data),
  update: (id, data) => api.put(`/reports/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/reports/${id}`).then((r) => r.data),
  exportContext: (childId, periodDays = 90) =>
    api.get("/reports/export/context", { params: { child_id: childId, period_days: periodDays } }).then((r) => r.data),
  // 学情周报/月报（v1.7.0）
  generatePeriod: (childId, payload) =>
    api.post("/reports/period/generate", payload, { params: { child_id: childId } }).then((r) => r.data),
  listPeriod: (childId) =>
    api.get("/reports/period/list", { params: { child_id: childId } }).then((r) => r.data),
  deletePeriod: (id) => api.delete(`/reports/period/${id}`).then((r) => r.data),
};

export default api;

export const configAPI = {
  get: () => api.get("/config").then((r) => r.data),
};

export const knowledgePointsAPI = {
  list: (params) => api.get("/knowledge-points", { params }).then((r) => r.data),
  listSubjects: () => api.get("/knowledge-points/subjects").then((r) => r.data),
  listCategories: () => api.get("/knowledge-points/categories").then((r) => r.data),
  listGradeLevels: () => api.get("/knowledge-points/grade-levels").then((r) => r.data),
  get: (id) => api.get(`/knowledge-points/${id}`).then((r) => r.data),
  create: (data) => api.post("/knowledge-points", data).then((r) => r.data),
  update: (id, data) => api.put(`/knowledge-points/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/knowledge-points/${id}`).then((r) => r.data),
};

export const importExportAPI = {
  exportExams: (params) => api.get("/import-export/exams", { params, responseType: "blob" }).then((r) => r.data),
  exportHomeworks: (params) => api.get("/import-export/homeworks", { params, responseType: "blob" }).then((r) => r.data),
  importExams: (file, childId) => {
    const form = new FormData();
    form.append("file", file);
    if (childId) form.append("child_id", String(childId));
    return api.post("/import-export/exams", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  importHomeworks: (file, childId) => {
    const form = new FormData();
    form.append("file", file);
    if (childId) form.append("child_id", String(childId));
    return api.post("/import-export/homeworks", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
};

export const wrongQuestionsAPI = {
  list: (params) => api.get("/wrong-questions", { params }).then((r) => r.data),
  get: (id) => api.get(`/wrong-questions/${id}`).then((r) => r.data),
  create: (data) => api.post("/wrong-questions", data).then((r) => r.data),
  update: (id, data) => api.put(`/wrong-questions/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/wrong-questions/${id}`).then((r) => r.data),
  stats: (childId) => api.get(`/wrong-questions/stats/${childId}`).then((r) => r.data),
  today: (childId) => api.get(`/wrong-questions/today/${childId}`).then((r) => r.data),
  review: (id, result) => api.post(`/wrong-questions/${id}/review`, { result }).then((r) => r.data),
  match: (id) => api.get(`/wrong-questions/${id}/match`).then((r) => r.data),
  applyMatch: (id, data) => api.post(`/wrong-questions/${id}/apply-match`, data).then((r) => r.data),
};

// ============ 题库系统 ============
export const questionBanksAPI = {
  list: (params) => api.get("/question-banks", { params }).then((r) => r.data),
  get: (id) => api.get(`/question-banks/${id}`).then((r) => r.data),
  create: (data) => api.post("/question-banks", data).then((r) => r.data),
  update: (id, data) => api.put(`/question-banks/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/question-banks/${id}`).then((r) => r.data),
  listQuestions: (bankId, params) => api.get(`/question-banks/${bankId}/questions`, { params }).then((r) => r.data),
  createQuestion: (bankId, data) => api.post(`/question-banks/${bankId}/questions`, data).then((r) => r.data),
  updateQuestion: (bankId, qid, data) => api.put(`/question-banks/${bankId}/questions/${qid}`, data).then((r) => r.data),
  deleteQuestion: (bankId, qid) => api.delete(`/question-banks/${bankId}/questions/${qid}`).then((r) => r.data),
  startExercise: (data) => api.post("/question-banks/exercises/start", data).then((r) => r.data),
  submitExercise: (exerciseId, answers, timeSpent) => api.post(`/question-banks/exercises/${exerciseId}/submit`, { answers, time_spent: timeSpent }).then((r) => r.data),
  getExercise: (exerciseId) => api.get(`/question-banks/exercises/${exerciseId}`).then((r) => r.data),
  listExercises: (childId) => api.get("/question-banks/exercises", { params: { child_id: childId } }).then((r) => r.data),
  recommend: (childId) => api.get(`/question-banks/recommend/${childId}`).then((r) => r.data),
};

// ============ 生长发育 ============
export const growthAPI = {
  list: (childId) => api.get(`/growth/${childId}`).then((r) => r.data),
  create: (childId, data) => api.post(`/growth/${childId}`, data).then((r) => r.data),
  update: (id, data) => api.put(`/growth/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/growth/${id}`).then((r) => r.data),
};

// ============ 社交情感 ============
export const socialEmotionalAPI = {
  list: (childId) => api.get(`/social-emotional/${childId}`).then((r) => r.data),
  create: (childId, data) => api.post(`/social-emotional/${childId}`, data).then((r) => r.data),
  update: (id, data) => api.put(`/social-emotional/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/social-emotional/${id}`).then((r) => r.data),
};

// ============ 兴趣特长 ============
export const interestsAPI = {
  list: (childId) => api.get(`/interests/${childId}`).then((r) => r.data),
  create: (childId, data) => api.post(`/interests/${childId}`, data).then((r) => r.data),
  update: (id, data) => api.put(`/interests/${id}`, data).then((r) => r.data),
  remove: (id) => api.delete(`/interests/${id}`).then((r) => r.data),
};

// ============ 奖励系统 ============
export const rewardsAPI = {
  ranks: (childId) => api.get(`/rewards/ranks/${childId}`).then((r) => r.data),
  recalculateRanks: (childId) => api.post(`/rewards/ranks/${childId}/recalculate`).then((r) => r.data),
  points: (childId) => api.get(`/rewards/points/${childId}`).then((r) => r.data),
  examReward: (examId) => api.post(`/rewards/exam-reward/${examId}`).then((r) => r.data),
  shop: (childId) => api.get(`/rewards/shop/${childId}`).then((r) => r.data),
  redeem: (childId, rewardId) => api.post(`/rewards/redeem/${childId}/${rewardId}`).then((r) => r.data),
  rewardHistory: (childId) => api.get(`/rewards/history/${childId}`).then((r) => r.data),
  listRewards: () => api.get(`/rewards/rewards`).then((r) => r.data),
  createReward: (data) => api.post(`/rewards/rewards`, data).then((r) => r.data),
  updateReward: (id, data) => api.put(`/rewards/rewards/${id}`, data).then((r) => r.data),
  deleteReward: (id) => api.delete(`/rewards/rewards/${id}`).then((r) => r.data),
  listAchievements: () => api.get(`/rewards/achievements`).then((r) => r.data),
  createAchievement: (data) => api.post(`/rewards/achievements`, data).then((r) => r.data),
  childAchievements: (childId) => api.get(`/rewards/achievements/${childId}`).then((r) => r.data),
  pointsLog: (childId, limit) => api.get(`/rewards/points-log/${childId}`, { params: { limit } }).then((r) => r.data),
};

// ============ 教材章节 / 学习进度 / Project 作品 ============
export const textbookAPI = {
  listVersions: (params) => api.get("/textbook/versions", { params }).then((r) => r.data),
  getVersion: (id) => api.get(`/textbook/versions/${id}`).then((r) => r.data),
  listUnits: (versionId) => api.get(`/textbook/versions/${versionId}/units`).then((r) => r.data),
  getUnit: (id) => api.get(`/textbook/units/${id}`).then((r) => r.data),
  getQuestionUnits: (qid) => api.get(`/textbook/questions/${qid}/units`).then((r) => r.data),
  linkQuestionUnits: (qid, links) => api.post(`/textbook/questions/${qid}/units`, links).then((r) => r.data),
  questionIdsForUnit: (unitId) => api.post(`/textbook/units/${unitId}/questions`).then((r) => r.data),
  listKnowledgePointsForUnit: (unitId) => api.get(`/knowledge-point-units/unit/${unitId}`).then((r) => r.data),
};

export const studyProgressAPI = {
  getSummary: (childId, versionId) => api.get(`/study-progress/child/${childId}/version/${versionId}`).then((r) => r.data),
  getForUnit: (childId, unitId) => api.get(`/study-progress/child/${childId}/unit/${unitId}`).then((r) => r.data),
};

export const projectWorksAPI = {
  list: (params) => api.get("/project-works", { params }).then((r) => r.data),
  submit: (data) => api.post("/project-works", data).then((r) => r.data),
  uploadImage: (id, file) => {
    const form = new FormData();
    form.append("file", file);
    return api.post(`/project-works/${id}/upload`, form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
  review: (id, data) => api.put(`/project-works/${id}/review`, data).then((r) => r.data),
  remove: (id) => api.delete(`/project-works/${id}`).then((r) => r.data),
};

// ============ KP 学习进度（知识点级别掌握度） ============
export const kpProgressAPI = {
  getForUnit: (childId, unitId) => api.get(`/kp-progress/child/${childId}/unit/${unitId}`).then((r) => r.data),
  getForVersion: (childId, versionId) => api.get(`/kp-progress/child/${childId}/version/${versionId}`).then((r) => r.data),
  getForKP: (childId, kpId) => api.get(`/kp-progress/child/${childId}/kp/${kpId}`).then((r) => r.data),
};

// ============ 系统（版本 + 升级） ============
export const systemAPI = {
  getVersion: () => api.get("/system/version").then((r) => r.data),
  getUpgradeLog: () => api.get("/system/upgrade-log").then((r) => r.data),
  triggerUpgrade: () => api.post("/system/upgrade").then((r) => r.data),
};

// ============ Question ↔ KP 关联 ============
export const questionKPAPI = {
  getForQuestion: (qid) => api.get(`/question-knowledge-points/question/${qid}`).then((r) => r.data),
  getForKP: (kpId) => api.get(`/question-knowledge-points/knowledge-point/${kpId}`).then((r) => r.data),
  link: (qid, links) => api.post(`/question-knowledge-points/question/${qid}`, links).then((r) => r.data),
  bulkLink: (payload) => api.post("/question-knowledge-points/bulk", payload).then((r) => r.data),
  bankSummary: (bankId) => api.get(`/question-knowledge-points/bank/${bankId}/summary`).then((r) => r.data),
};
