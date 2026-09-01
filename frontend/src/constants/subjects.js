// 关注科目录入：8 个预设 + 「自定义」选项
// 「自定义」走 inline 输入框，名字可任意
// 顺序按"小学 → 中学"惯例排列
export const PRESET_SUBJECTS = [
  "语文",
  "数学",
  "英语",
  "科学",
  "信息科技",
  "生物",
  "地理",
  "物理",
];

// 校验：用 Set 加速判断
export const PRESET_SUBJECTS_SET = new Set(PRESET_SUBJECTS);

// 给 chip 加颜色（按学段语义分组）：小学基础 / 中学科目
export const SUBJECT_COLOR_MAP = {
  语文: "bg-rose-100 text-rose-700 border-rose-200",
  数学: "bg-blue-100 text-blue-700 border-blue-200",
  英语: "bg-violet-100 text-violet-700 border-violet-200",
  科学: "bg-emerald-100 text-emerald-700 border-emerald-200",
  信息科技: "bg-cyan-100 text-cyan-700 border-cyan-200",
  生物: "bg-teal-100 text-teal-700 border-teal-200",
  地理: "bg-amber-100 text-amber-700 border-amber-200",
  物理: "bg-indigo-100 text-indigo-700 border-indigo-200",
};

// 自定义科目 chip 用中性灰
export const CUSTOM_SUBJECT_COLOR = "bg-slate-100 text-slate-700 border-slate-200";