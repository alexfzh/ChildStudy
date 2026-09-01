import { defineStore } from "pinia";
import { childrenAPI, configAPI } from "@/api";

export const useChildStore = defineStore("child", {
  state: () => ({
    children: [],
    currentId: null,
    gradeHistoryMap: {}, // { childId: [{id, grade, effective_from, note, created_at}, ...] }
    maxChildren: 4, // 服务端动态下发，默认 4
  }),
  getters: {
    current(state) {
      return state.children.find((c) => c.id === state.currentId) || null;
    },
    hasChildren(state) {
      return state.children.length > 0;
    },
    currentGradeHistory(state) {
      return state.gradeHistoryMap[state.currentId] || [];
    },
    canAddMore(state) {
      return state.children.length < state.maxChildren;
    },
  },
  actions: {
    async loadConfig() {
      try {
        const cfg = await configAPI.get();
        this.maxChildren = cfg.max_children ?? 4;
      } catch {
        // keep default
      }
    },
    async loadChildren() {
      this.children = await childrenAPI.list();
      // 优先用 localStorage 记住当前选中
      const saved = Number(localStorage.getItem("currentChildId"));
      if (saved && this.children.find((c) => c.id === saved)) {
        this.currentId = saved;
      } else {
        // 防御性清理：saved 指向的 child 已不存在（被删/被 CASCADE）
        // 显式清掉 localStorage，避免下次加载再读同一个无效 id
        if (saved && !this.children.find((c) => c.id === saved)) {
          localStorage.removeItem("currentChildId");
        }
        if (this.children.length > 0) {
          this.currentId = this.children[0].id;
        }
      }
      // 加载所有 child 的年级历史（轻量，不阻塞）
      await this.loadAllGradeHistory();
    },
    async loadAllGradeHistory() {
      const results = await Promise.all(
        this.children.map(async (c) => {
          try {
            const history = await childrenAPI.listGradeHistory(c.id);
            return [c.id, history];
          } catch {
            return [c.id, []];
          }
        })
      );
      for (const [id, history] of results) {
        this.gradeHistoryMap[id] = history;
      }
    },
    async loadGradeHistory(childId) {
      this.gradeHistoryMap[childId] = await childrenAPI.listGradeHistory(childId);
      return this.gradeHistoryMap[childId];
    },
    async addGradeHistory(childId, data) {
      const entry = await childrenAPI.addGradeHistory(childId, data);
      // 本地更新 child.grade
      const child = this.children.find((c) => c.id === childId);
      if (child) child.grade = entry.grade;
      // 重新拉历史
      await this.loadGradeHistory(childId);
      return entry;
    },
    async removeGradeHistory(childId, historyId) {
      await childrenAPI.removeGradeHistory(childId, historyId);
      await this.loadGradeHistory(childId);
    },
    setCurrent(id) {
      this.currentId = id;
      localStorage.setItem("currentChildId", String(id));
    },
    // 孩子账号后端禁止访问 /api/children（仅家长可列），无法用 loadChildren。
    // 直接用登录返回的 child_id + display_name 自举一个最小 child 对象，
    // 使各页面通过 childStore.currentId 取数，无需“选择孩子”。
    bootstrapChild(child) {
      this.children = [{ id: child.id, name: child.name }];
      this.currentId = child.id;
      localStorage.setItem("currentChildId", String(child.id));
    },
    async create(data) {
      const child = await childrenAPI.create(data);
      this.children.push(child);
      this.gradeHistoryMap[child.id] = [];
      if (!this.currentId) this.setCurrent(child.id);
      return child;
    },
    async update(id, data) {
      const child = await childrenAPI.update(id, data);
      const idx = this.children.findIndex((c) => c.id === id);
      if (idx >= 0) this.children[idx] = child;
      return child;
    },
    async remove(id) {
      await childrenAPI.remove(id);
      this.children = this.children.filter((c) => c.id !== id);
      delete this.gradeHistoryMap[id];
      if (this.currentId === id) {
        this.currentId = this.children[0]?.id ?? null;
        if (this.currentId) localStorage.setItem("currentChildId", String(this.currentId));
        else localStorage.removeItem("currentChildId");
      }
    },
  },
});