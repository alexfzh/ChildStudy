import { defineStore } from "pinia";
import { authAPI } from "@/api";

export const useAuthStore = defineStore("auth", {
  state: () => ({
    token: localStorage.getItem("access_token") || null,
    user: JSON.parse(localStorage.getItem("user") || "null"),
    accessibleChildIds: JSON.parse(localStorage.getItem("accessible_child_ids") || "[]"),
    needsSetup: false,
  }),
  getters: {
    isAuthenticated: (s) => !!s.token,
    isParent: (s) => s.user?.role === "parent",
    isChild: (s) => s.user?.role === "child",
    currentChildId: (s) => (s.isChild ? s.user?.child_id : null),
  },
  actions: {
    async checkSetup() {
      const r = await authAPI.setupStatus();
      this.needsSetup = r.needs_setup;
      return r.needs_setup;
    },
    async setup({ familyName, username, password, displayName }) {
      const r = await authAPI.setup({
        family_name: familyName,
        username,
        password,
        display_name: displayName,
      });
      this._persist(r.access_token, r.user, null);
      this.needsSetup = false;
      return r.user;
    },
    async login(username, password) {
      const r = await authAPI.login({ username, password });
      const me = await authAPI.me(r.access_token);
      this._persist(r.access_token, r.user, me.accessible_child_ids);
      return r.user;
    },
    async refreshMe() {
      if (!this.token) return;
      try {
        const me = await authAPI.me(this.token);
        this.accessibleChildIds = me.accessible_child_ids;
        localStorage.setItem("accessible_child_ids", JSON.stringify(me.accessible_child_ids));
      } catch (e) {
        if (e.response?.status === 401) this.logout();
      }
    },
    logout() {
      this.token = null;
      this.user = null;
      this.accessibleChildIds = [];
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      localStorage.removeItem("accessible_child_ids");
    },
    _persist(token, user, accessible) {
      this.token = token;
      this.user = user;
      if (accessible !== null) {
        this.accessibleChildIds = accessible;
        localStorage.setItem("accessible_child_ids", JSON.stringify(accessible));
      }
      localStorage.setItem("access_token", token);
      localStorage.setItem("user", JSON.stringify(user));
    },
  },
});