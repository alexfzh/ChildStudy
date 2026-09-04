// ESLint 配置：与 ruff.toml 风格对齐（保守、注释清楚每条规则为什么）。
//
// 规则选择思路：
// - eslint:recommended            — JS 基础质量（未使用变量、相等性等）
// - plugin:vue/vue3-recommended   — Vue3 SFC 必备（v-html 警告、key 要求等）
// - eslint-config-prettier        — 关掉与 prettier 冲突的格式类规则
//
// 与 ruff.toml 不同的取舍：
// - 关闭 vue/multi-word-component-names：项目里有 App.vue 这种单词组件
// - 关闭 no-v-html：element-plus 部分组件（popper 等）依赖 innerHTML
// - no-console 仅禁止 log，允许 warn/error（全局错误边界/兜底日志要保留）
// - 关闭 vue/no-mutating-props：父传子的 props 直接修改在 router store 流转中偶有出现，先不拦
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true,
  },
  extends: ["eslint:recommended", "plugin:vue/vue3-recommended", "prettier"],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: "module",
  },
  rules: {
    "no-console": ["error", { allow: ["warn", "error"] }],
    "vue/multi-word-component-names": "off",
    "vue/no-v-html": "off",
    "vue/attribute-hyphenation": "off", // 项目里既有 :foo-bar 又有 :fooBar，暂不强制
    "vue/v-on-event-hyphenation": "off",
    "vue/require-toggle-inside-transition": "off", // 路由 fade 切换的标准模式（Component 由 v-slot 动态切换）
    "vue/no-unused-vars": "off", // 模板里未使用变量在 v-for 第二参数里常出现，由 vue/no-unused-vars 单文件级管控
    "vue/no-template-shadow": "off", // 嵌套 v-for 用同名 idx 是常见写法，逐处改名收益低
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
  },
  overrides: [
    {
      // main.js / 配置文件允许 console（启动期调试可能用到）
      files: ["src/main.js", "src/router/**/*.js", "src/stores/**/*.js"],
      rules: {
        "no-console": "off",
      },
    },
    {
      // 单测文件放开更严的规则（未使用变量在 mock 时是常态）
      // 注：vitest 单测第二批再引入；先把目录占位写好，避免后续开第二战场再改配置
      files: ["tests/**/*.{js,vue}", "**/*.spec.js", "**/*.test.js"],
      env: { jest: true },
      rules: {
        "no-unused-vars": "off",
      },
    },
  ],
  ignorePatterns: [
    "dist/**",
    "node_modules/**",
    "*.min.js",
    // 按需生成的自动 import 解析器产物
    "auto-imports.d.ts",
    "components.d.ts",
  ],
}
