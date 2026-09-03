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
    r = assess_bmi(15.0, "male", 5 * 12)
    assert r["category"] == "approximate"


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
    assert data["schema_version"] == 1
    assert "height_0_83_months" in data
    assert "bmi_cutoffs_6_18" in data
    assert "male" in data["height_0_83_months"]
    assert len(data["height_0_83_months"]["male"]) == 84
