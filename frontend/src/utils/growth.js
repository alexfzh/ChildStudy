/**
 * Growth page utilities.
 *
 * - fetchStandards(): GET /api/growth/standards
 * - computeBMI(height_cm, weight_kg)
 * - assessBMI(bmi, gender, age_months) -> { category, label, color }
 * - getPercentileLabel(category) -> string
 */

const API_BASE = import.meta.env.VITE_API_BASE || ""

// Cache standards in memory (they don't change during session)
let _standardsCache = null

export async function fetchStandards() {
  if (_standardsCache) return _standardsCache
  const res = await fetch(`${API_BASE}/api/growth/standards`)
  if (!res.ok) throw new Error(`Failed to fetch standards: ${res.status}`)
  _standardsCache = await res.json()
  return _standardsCache
}

export function computeBMI(heightCm, weightKg) {
  if (!heightCm || !weightKg || heightCm <= 0 || weightKg <= 0) return null
  const h = heightCm / 100
  return Math.round((weightKg / (h * h)) * 100) / 100
}

/**
 * BMI category based on WS/T 586-2018 (6-18岁) or WS/T 423-2022 (<7岁).
 * Returns { category, label, color, source }
 *
 * 2026-09-05 复核后口径调整：0-83 月 P85-P97 与 ≥P97 均标为「超重」/
 * 「肥胖」，与后端 assess_bmi 保持一致（之前前端用了「偏胖」一词，
 * 与后端「超重」不一致）。
 */
export function assessBMI(bmi, gender, ageMonths) {
  if (bmi == null || ageMonths == null) {
    return { category: "unknown", label: "-", color: "default", source: "-" }
  }
  const g = (gender || "male").toLowerCase()
  if (ageMonths <= 83) {
    // 0-83 月: WS/T 423-2022 百分位法
    const row = _standardsCache?.bmi_0_83_months?.[g]?.[String(ageMonths)]
    if (!row) return { category: "unknown", label: "-", color: "default", source: "-" }
    const [p3, p15, p50, p85, p97] = row
    if (bmi < p3) return { category: "thin", label: "偏瘦", color: "info", source: "WS/T 423-2022（百分位法）" }
    if (bmi < p15) return { category: "thin", label: "偏瘦", color: "info", source: "WS/T 423-2022（百分位法）" }
    if (bmi <= p50) return { category: "normal", label: "正常", color: "success", source: "WS/T 423-2022（百分位法）" }
    if (bmi <= p85) return { category: "normal", label: "正常", color: "success", source: "WS/T 423-2022（百分位法）" }
    if (bmi < p97)
      return { category: "overweight", label: "超重", color: "warning", source: "WS/T 423-2022（百分位法）" }
    return { category: "obese", label: "肥胖", color: "danger", source: "WS/T 423-2022（百分位法）" }
  }
  if (ageMonths > 216) {
    return { category: "unknown", label: "-", color: "default", source: "-" }
  }
  // 6-18 岁: WS/T 586-2018（超重/肥胖）+ WS/T 456-2014（消瘦）
  const ageStr = String(Math.round((ageMonths / 12) * 2) / 2)
  const cutoffs = _standardsCache?.bmi_cutoffs_6_18?.[g]?.[ageStr]
  if (!cutoffs) {
    return { category: "unknown", label: "-", color: "default", source: "-" }
  }
  const thin = _standardsCache?.bmi_thin_cutoffs_6_18?.[g]?.[ageStr]
  const [ow, ob] = cutoffs
  if (bmi >= ob) return { category: "obese", label: "肥胖", color: "danger", source: "WS/T 586-2018", cutoff: cutoffs }
  if (bmi >= ow)
    return { category: "overweight", label: "超重", color: "warning", source: "WS/T 586-2018", cutoff: cutoffs }
  if (thin && bmi <= thin[1]) {
    // WS/T 456-2014: thin = [中重度消瘦界, 轻度消瘦界]
    if (bmi <= thin[0])
      return { category: "severe_thin", label: "中重度消瘦", color: "danger", source: "WS/T 456-2014", cutoff: cutoffs, thinCutoff: thin }
    return { category: "thin", label: "偏瘦（轻度消瘦）", color: "info", source: "WS/T 456-2014", cutoff: cutoffs, thinCutoff: thin }
  }
  return { category: "normal", label: "正常", color: "success", source: "WS/T 586-2018", cutoff: cutoffs }
}

/**
 * Height/weight percentile label from category.
 */
export function getPercentileLabel(category) {
  const map = {
    down: "下（<P3）",
    mid_down: "中下",
    mid: "中",
    mid_up: "中上",
    up: "上（≥P97）",
    unknown: "-",
    approximate: "需医生评估",
  }
  return map[category] || "-"
}

export const BMI_COLORS = {
  normal: "#10b981",
  overweight: "#f59e0b",
  obese: "#ef4444",
  thin: "#0ea5e9",
  severe_thin: "#e11d48",
  unknown: "#94a3b8",
  approximate: "#6366f1",
}

// In-memory standards reference (set after fetchStandards)
export function setStandards(data) {
  _standardsCache = data
}

export function getStandards() {
  return _standardsCache
}
