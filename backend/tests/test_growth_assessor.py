"""Growth assessor + standards endpoint tests."""
from __future__ import annotations

import pytest

from utils.growth_assessor import assess_bmi, assess_height, compute_bmi
from utils.growth_standards import BMI_CUTOFFS_6_18


# ---- compute_bmi ----
@pytest.mark.parametrize("h,w,expected", [
    (100, 15, 15.0),
    (120, 27, 18.75),
    (130, 45, 26.63),
])
def test_compute_bmi(h, w, expected):
    assert compute_bmi(h, w) == expected


def test_compute_bmi_zero():
    assert compute_bmi(0, 50) is None
    assert compute_bmi(100, 0) is None
    assert compute_bmi(None, 50) is None


# ---- assess_bmi (6-18 岁, WS/T 586-2018) ----
def test_bmi_overweight_male_10y():
    # 10.0 岁男: overweight=19.2, obesity=21.9
    r = assess_bmi(20.0, "male", 120)
    assert r["category"] == "overweight"
    assert r["label"] == "超重"
    assert r["color"] == "warning"


def test_bmi_obese_female_12y():
    # 12.0 岁女: overweight=21.5, obesity=23.9
    r = assess_bmi(24.0, "female", 12 * 12)
    assert r["category"] == "obese"
    assert r["label"] == "肥胖"
    assert r["color"] == "danger"


def test_bmi_normal_male_8y():
    # 8.0 岁男: overweight=17.8, obesity=19.7
    r = assess_bmi(16.0, "male", 8 * 12)
    assert r["category"] == "normal"
    assert r["label"] == "正常"
    assert r["color"] == "success"


def test_bmi_unknown_under_6y():
    # 5 岁男 (60 月) BMI P15=14.15, P50=15.3 (WS/T 423-2022 表 A.9)
    # 14.0 < P15 → 偏瘦
    r = assess_bmi(14.0, "male", 5 * 12)
    assert r["category"] == "thin"


def test_bmi_cutoff_table_consistency():
    # Every age in 6-18 should have 2 floats [overweight, obesity]
    for g in ("male", "female"):
        for age_str, vals in BMI_CUTOFFS_6_18[g].items():
            assert len(vals) == 2
            assert vals[0] < vals[1], f"{g} {age_str}: overweight >= obesity"


# ---- assess_height (0-83 月) ----
def test_height_male_6m():
    # 6 月男: P3=64.2, P15≈65.85, P50=68.7, P85≈71.45, P97=73.2
    r = assess_height(68.7, "male", 6)
    assert r["category"] == "mid"  # at P50
    assert r["label"] == "中"


def test_height_male_6m_above_p97():
    r = assess_height(75.0, "male", 6)
    assert r["category"] == "up"
    assert r["label"] == "上（≥P97）"


def test_height_female_3y():
    r = assess_height(95.4, "female", 36)  # at P50 (3岁女 P50=95.4cm)
    assert r["category"] == "mid"


# ---- standards endpoint (direct call) ----
def test_standards_direct():
    from routers.growth import get_standards
    data = get_standards()
    # 2026-09-05 复核后 schema_version 升到 2（标注 WS/T 612 + 7-18 岁体重非国标）
    assert data["schema_version"] == 2
    assert "height_0_83_months" in data
    assert "bmi_cutoffs_6_18" in data
    assert "bmi_0_83_months" in data
    assert "male" in data["height_0_83_months"]
    assert len(data["height_0_83_months"]["male"]) == 84
    assert len(data["bmi_0_83_months"]["male"]) == 84


# ---- assess_bmi 0-83 月 WS/T 423-2022 ----
def test_bmi_0_83_normal_p50():
    # 1 岁男 P50 = 17.1 (WS/T 423-2022 表 A.9, 2026-09-05 复核)
    r = assess_bmi(17.1, "male", 12)
    assert r["category"] == "normal"
    assert r["source"] == "WS/T 423-2022（百分位法）"


def test_bmi_0_83_thin_below_p3():
    # 1 岁男 P3 = 14.9
    r = assess_bmi(14.0, "male", 12)
    assert r["category"] == "thin"
    assert r["label"] == "偏瘦"


def test_bmi_0_83_obese_above_p97():
    # 1 岁男 P97 = 20.1
    r = assess_bmi(20.5, "male", 12)
    assert r["category"] == "obese"
    assert r["label"] == "肥胖"


def test_bmi_0_83_overweight_p85_to_p97():
    # 1 岁男 P85=18.6, P97=20.1 -> 19.5 应该在 mid_up 区间 → 超重
    r = assess_bmi(19.5, "male", 12)
    assert r["category"] == "overweight"
    assert r["label"] == "超重"


def test_bmi_0_83_female_p50():
    # 1 岁女 P50 = 16.7
    r = assess_bmi(16.7, "female", 12)
    assert r["category"] == "normal"


def test_bmi_0_83_3year_old():
    # 3 岁男 (36 月) P50 = 15.5
    r = assess_bmi(15.5, "male", 36)
    assert r["category"] == "normal"


# ---- assess_height 7-18 岁 WS/T 612-2018 (2026-09-05 复核) ----
def test_height_male_13y_at_median():
    # 13 岁男 中位数 = 160.19 (WS/T 612-2018)
    # WS/T 612 仅 3 档 [-2SD, 中位数, +2SD]，代码规则 P3≤v≤P50 落「中下」、
    # P50<v≤P97 落「中上」，故「正中等」以 P50 为分界线。
    r = assess_height(160.19, "male", 13 * 12)
    assert r["category"] == "mid_down"
    assert r["source"] == "WS/T 612-2018（SD 法）"
    # 161 cm 应在 (P50, P97] 区间 → 中上
    r2 = assess_height(161.0, "male", 13 * 12)
    assert r2["category"] == "mid_up"


def test_height_female_3y_corrected():
    # 3 岁女 P50 = 96.2 (WS/T 423-2022, 修复前错误值 95.4)
    r = assess_height(96.2, "female", 36)
    assert r["category"] == "mid"


def test_weight_male_60m_corrected():
    # 5 岁男 (60 月) P50 = 19.1 kg (WS/T 423-2022, 修复前错误值 23.3 kg)
    # 60 月体重表: P3=15.3, P15=17.0, P50=19.1, P85=21.55, P97=24.2
    # 22.0 kg 落在 P85-P97 区间 → "上"
    # 修复前 22 kg 在旧表里会被判为 mid（<旧P50=23.3），会把"上"的娃误判为"中"
    from utils.growth_assessor import assess_weight
    r = assess_weight(22.0, "male", 60)
    assert r["category"] == "up"
    assert r["label"] == "上（≥P97）"
    # 边界 15 kg 落在 P3 之下
    r2 = assess_weight(15.0, "male", 60)
    assert r2["category"] == "down"
    # 18 kg 落在 P15-P50 区间 (中)
    r3 = assess_weight(18.0, "male", 60)
    assert r3["category"] == "mid"
