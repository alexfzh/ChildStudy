"""Growth assessment utilities.

Uses data from growth_standards.py (WS/T 423-2022, WS/T 586-2018, WS/T 611-2018).
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal

from .growth_standards import (
    BMI_0_83,
    BMI_CUTOFFS_6_18,
    HEIGHT_0_83,
    HEIGHT_7_18,
    WEIGHT_0_83,
    WEIGHT_7_18,
)

Gender = Literal["male", "female"]


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(Decimal(str(v)))
    except (InvalidOperation, ValueError):
        return None


def compute_bmi(height_cm: float | None, weight_kg: float | None) -> float | None:
    """BMI = weight(kg) / height(m)^2."""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    h_m = height_cm / 100
    return round(weight_kg / (h_m * h_m), 2)


def _months_from_date(birth_date: str | None, record_date: str | None) -> int | None:
    """Calculate age in months from birth_date to record_date."""
    from datetime import date

    from dateutil.relativedelta import relativedelta

    if not birth_date or not record_date:
        return None
    try:
        bd = date.fromisoformat(birth_date)
        rd = date.fromisoformat(record_date)
        rd_ = relativedelta(rd, bd)
        return rd_.years * 12 + rd_.months
    except Exception:
        return None


def _lookup_0_83(
    gender: Gender, age_months: int, value: float, table: dict
) -> tuple[str, float | None]:
    """Locate percentile for 0-83 month table."""
    if age_months < 0 or age_months > 83:
        return ("unknown", None)
    row = table.get(gender, {}).get(age_months)
    if not row:
        return ("unknown", None)
    p3, p15, p50, p85, p97 = row
    if value < p3:
        return ("down", None)
    elif value < p15:
        # between P3 and P15: estimate percentile
        if p15 > p3:
            est = 3 + (value - p3) / (p15 - p3) * 12
        else:
            est = 3
        return ("mid_down", round(est, 1))
    elif value <= p50:
        if p50 > p15:
            est = 15 + (value - p15) / (p50 - p15) * 35
        else:
            est = 15
        return ("mid", round(est, 1))
    elif value <= p85:
        if p85 > p50:
            est = 50 + (value - p50) / (p85 - p50) * 35
        else:
            est = 50
        return ("mid_up", round(est, 1))
    elif value < p97:
        if p97 > p85:
            est = 85 + (value - p85) / (p97 - p85) * 12
        else:
            est = 85
        return ("up", round(est, 1))
    else:
        return ("up", 97.0)


def _lookup_7_18(
    gender: Gender, age_years: float, value: float, table: dict
) -> tuple[str, float | None]:
    """Locate percentile for 7-18 year table.

    表的列格式：
    - 5 档 (P3/P15/P50/P85/P97，对应 WS/T 612-2018 SD 法 -2SD/-1SD/中位/+1SD/+2SD)：
      下(<P3) / 中下(P3-P15) / 中(P15-P85) / 中上(P85-P97) / 上(≥P97)
    - 3 档 (P3/P50/P97，旧格式)：下(<P3) / 中下(P3-P50) / 中上(P50-P97) / 上(≥P97)
    """
    yr = int(age_years)
    if yr < 7 or yr > 18:
        return ("unknown", None)
    row = table.get(gender, {}).get(yr)
    if not row:
        return ("unknown", None)
    if len(row) >= 5:
        p3, p15, p50, p85, p97 = row
        if value < p3:
            return ("down", None)
        if value <= p15:
            est = 3 + (value - p3) / (p15 - p3) * 12 if p15 > p3 else 3
            return ("mid_down", round(est, 1))
        if value <= p85:
            # P15-P85 占整体约 70% (15.9→84.1)，按比例估
            if p85 > p15:
                est = 15 + (value - p15) / (p85 - p15) * 70
            else:
                est = 15
            return ("mid", round(est, 1))
        if value <= p97:
            if p97 > p85:
                est = 85 + (value - p85) / (p97 - p85) * 12
            else:
                est = 85
            return ("mid_up", round(est, 1))
        return ("up", 97.0)
    # 3 档兼容（保留旧数据形态）
    p3, p50, p97 = row
    if value < p3:
        return ("down", None)
    elif value <= p50:
        if p50 > p3:
            est = 3 + (value - p3) / (p50 - p3) * 47
        else:
            est = 3
        return ("mid_down", round(est, 1))
    elif value <= p97:
        if p97 > p50:
            est = 50 + (value - p50) / (p97 - p50) * 47
        else:
            est = 50
        return ("mid_up", round(est, 1))
    else:
        return ("up", 97.0)


def assess_height(height_cm: float | None, gender: Gender, age_months: int | None) -> dict:
    """Return height assessment: {category, label, percentile, source}."""
    h = _to_float(height_cm)
    if not h or age_months is None:
        return {"category": "unknown", "label": "-", "percentile": None, "source": "-"}
    if age_months <= 83:
        cat, pct = _lookup_0_83(gender, age_months, h, HEIGHT_0_83)
        src = "WS/T 423-2022"
    elif age_months <= 216:
        yr = age_months / 12
        cat, pct = _lookup_7_18(gender, yr, h, HEIGHT_7_18)
        # 7-18 岁身高标准编号是 WS/T 612-2018（不是 611），标准采用 SD 法
        src = "WS/T 612-2018（SD 法）"
    else:
        return {"category": "unknown", "label": "-", "percentile": None, "source": "-"}
    labels = {
        "down": "下（<P3）",
        "mid_down": "中下（P3-P15）",
        "mid": "中（P15-P85）",
        "mid_up": "中上（P85-P97）",
        "up": "上（≥P97）",
        "unknown": "-",
    }
    return {"category": cat, "label": labels[cat], "percentile": pct, "source": src}


def assess_weight(weight_kg: float | None, gender: Gender, age_months: int | None) -> dict:
    """Return weight assessment: {category, label, percentile, source}."""
    w = _to_float(weight_kg)
    if not w or age_months is None:
        return {"category": "unknown", "label": "-", "percentile": None, "source": "-"}
    if age_months <= 83:
        cat, pct = _lookup_0_83(gender, age_months, w, WEIGHT_0_83)
        # 0-83 月有 WS/T 423-2022 国标
        src = "WS/T 423-2022"
    elif age_months <= 216:
        yr = age_months / 12
        cat, pct = _lookup_7_18(gender, yr, w, WEIGHT_7_18)
        # 7-18 岁体重国内无统一国标（WS/T 612-2018 仅覆盖身高），
        # 当前数据沿用首都儿科研究所九城市儿童体格发育调查 (2009)，
        # 仅作参考，应结合 BMI 切点（WS/T 586-2018）与医生评估综合判断。
        # 该调查表本身只给 P3/P50/P97 三档，分类粗一些。
        src = "九城市儿童体格发育调查 2009（非国标，参考）"
    else:
        return {"category": "unknown", "label": "-", "percentile": None, "source": "-"}
    labels = {
        "down": "下（<P3）",
        "mid_down": "中下",
        "mid": "中",
        "mid_up": "中上",
        "up": "上（≥P97）",
        "unknown": "-",
    }
    return {"category": cat, "label": labels[cat], "percentile": pct, "source": src}


def assess_bmi(bmi: float | None, gender: Gender, age_months: int | None) -> dict:
    """Return BMI assessment: {category, label, color, cutoff, source}."""
    b = _to_float(bmi)
    if not b or age_months is None:
        return {"category": "unknown", "label": "-", "color": "default", "cutoff": None, "source": "-"}
    if age_months <= 83:
        # 0-83 月: WS/T 423-2022 BMI 百分位法
        # 映射: <P15 偏瘦, P15-P85 正常, P85-P97 超重, ≥P97 肥胖
        row = BMI_0_83.get(gender, {}).get(age_months)
        if not row:
            return {"category": "unknown", "label": "-", "color": "default", "cutoff": None, "source": "-"}
        p3, p15, _p50, p85, p97 = row
        if b < p15:
            cat, label, color = "thin", "偏瘦", "info"
            pct = round(3 + (b - p3) / (p15 - p3) * 12, 1) if p15 > p3 else 3
        elif b <= p85:
            cat, label, color = "normal", "正常", "success"
            pct = round(15 + (b - p15) / (p85 - p15) * 70, 1) if p85 > p15 else 15
        elif b < p97:
            cat, label, color = "overweight", "超重", "warning"
            pct = round(85 + (b - p85) / (p97 - p85) * 12, 1) if p97 > p85 else 85
        else:
            cat, label, color = "obese", "肥胖", "danger"
            pct = 97.0
        return {
            "category": cat,
            "label": label,
            "color": color,
            "cutoff": None,
            "source": "WS/T 423-2022（百分位法）",
            "percentile": pct,
        }
    elif age_months <= 216:
        # 6-18 岁: WS/T 586-2018 超重/肥胖切点
        age_str = str(round(age_months / 12 * 2) / 2)  # nearest 0.5
        cutoff = BMI_CUTOFFS_6_18.get(gender, {}).get(age_str)
        if not cutoff:
            return {"category": "unknown", "label": "-", "color": "default", "cutoff": None, "source": "-"}
        ow, ob = cutoff
        if b >= ob:
            cat, label, color = "obese", "肥胖", "danger"
        elif b >= ow:
            cat, label, color = "overweight", "超重", "warning"
        else:
            cat, label, color = "normal", "正常", "success"
        return {"category": cat, "label": label, "color": color, "cutoff": cutoff, "source": "WS/T 586-2018"}
    else:
        return {"category": "unknown", "label": "-", "color": "default", "cutoff": None, "source": "-"}


def get_standard_description() -> dict:
    """Return human-readable description of growth standards (audited 2026-09-05).

    重要说明：
    - 0-7 岁（0-83 月）身高 / 体重 / BMI：WS/T 423-2022《7 岁以下儿童生长标准》
      国家卫健委 2022-09-19 发布，2023-03-01 实施。
    - 7-18 岁身高：WS/T 612-2018《7 岁～18 岁儿童青少年身高发育等级评价》
      国家卫健委 2018-06-15 发布，2018-12-01 实施；采用 SD 法（-2SD/中位数/+2SD），
      近似展示为 [P3, P50, P97]。
    - 6-18 岁 BMI 超重 / 肥胖切点：WS/T 586-2018《学龄儿童青少年超重与肥胖筛查》，
      每半岁一档 [超重界, 肥胖界]。
    - 7-18 岁体重（P3/P50/P97）：国内暂无统一国标。
      WS/T 612-2018 不覆盖体重，WS/T 586-2018 不给身高体重 P3/P50/P97。
      当前沿用首都儿科研究所九城市儿童体格发育调查（2009 报告），
      仅作参考，应结合 BMI 切点与医生评估综合判断。
    """
    return {
        "cn_0_7": {
            "title": "0-7 岁（WS/T 423-2022）",
            "desc": (
                "采用百分位数法。P3-P97 为正常范围，<P3 为偏瘦，"
                ">P97 为偏胖。0-83 月身高/体重/BMI 全部为国家标准。"
            ),
        },
        "cn_6_18": {
            "title": "6-18 岁（WS/T 586-2018）",
            "desc": (
                "采用性别年龄别 BMI 切点。超重 = BMI ≥ 超重界值且 < 肥胖界值；"
                "肥胖 = BMI ≥ 肥胖界值。"
            ),
            "cutoffs": BMI_CUTOFFS_6_18,
        },
        "cn_height_7_18": {
            "title": "7-18 岁身高（WS/T 612-2018）",
            "desc": (
                "采用 SD 法（-2SD / -1SD / 中位数 / +1SD / +2SD），系统近似展示为"
                " [P3, P15, P50, P85, P97]。"
                "<P3 为下，P3-P15 为中下，P15-P85 为中，P85-P97 为中上，≥P97 为上。"
            ),
        },
        "cn_weight_7_18": {
            "title": "7-18 岁体重（参考值）",
            "desc": (
                "⚠️ 国内暂无统一国家标准。当前沿用首都儿科研究所九城市儿童体格发育调查"
                "（2009 报告），仅作参考；建议结合 BMI 切点（WS/T 586-2018）与医生评估综合判断。"
            ),
        },
    }
