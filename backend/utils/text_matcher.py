"""智能文本匹配引擎：错题 → 题库题目 + 知识点

策略（多层信号融合，目标：让系统看起来"很聪明"）：
1. 数字指纹：题干中所有数字的集合 Jaccard（数学/物理题的数字几乎唯一标识一道题）
2. 字符 n-gram：2-gram + 3-gram 的 Jaccard 相似度
3. 选项结构：检测 A/B/C/D 选项（选择题特征）
4. 学科 / 年级过滤：先缩候选池
5. 知识点：KP.name 与文本的 n-gram 重叠 + 精确子串命中
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set, Tuple

# ============ 文本特征提取 ============

def _extract_numbers(text: str) -> Set[str]:
    """提取题干中所有数字（整数、小数、百分数、分数形如 1/3）"""
    tokens = re.findall(r"\d+\.?\d*%?|(?:\d+/\d+)", text)
    return set(tokens)


def _char_ngrams(text: str, n: int = 2) -> Set[str]:
    """字符级 n-gram（去空格，全角半角统一为半角）"""
    s = text.replace(" ", "").replace("　", "")
    # 全角数字 → 半角
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _has_options(text: str) -> bool:
    """检测是否包含 A/B/C/D 选项（选择题特征）"""
    return bool(re.search(r"\b[ABCD]\.\s|选项\s*[ABCD]\b", text))


# ============ 数据结构 ============

@dataclass
class BankMatchCandidate:
    question_id: int
    bank_id: int
    bank_title: str
    content: str
    knowledge_point: str
    score: float  # 0-1 综合得分
    text_score: float = 0.0
    fingerprint_score: float = 0.0
    options_score: float = 0.0
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class KPMatchCandidate:
    knowledge_point_id: int
    name: str
    subject: str
    score: float
    match_reasons: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    bank_matches: List[BankMatchCandidate] = field(default_factory=list)
    kp_matches: List[KPMatchCandidate] = field(default_factory=list)


# ============ 题库匹配 ============

def match_question_bank(
    text: str,
    subject: str,
    db_questions: List[Tuple[int, int, str, str, str]],  # (qid, bank_id, bank_title, content, knowledge_point)
    top_k: int = 3,
) -> List[BankMatchCandidate]:
    """对一段错题文本，从候选题库题目中找最相似的题目。

    db_questions 由调用方从数据库查好传入（方便做 subject/grade 预过滤）。
    """
    if not text or not db_questions:
        return []

    text_nums = _extract_numbers(text)
    text_ngrams = _char_ngrams(text, 2) | _char_ngrams(text, 3)
    text_has_opts = _has_options(text)
    text_len = len(text)

    scored: List[BankMatchCandidate] = []
    for qid, bank_id, bank_title, content, kp in db_questions:
        # 长度过滤：差异 > 5 倍直接跳过（避免短题匹配长题干）
        c_len = len(content)
        if text_len > 0 and c_len > 0:
            ratio = max(text_len, c_len) / min(text_len, c_len)
            if ratio > 5.0:
                continue

        # 数字指纹
        q_nums = _extract_numbers(content)
        fp_score = _jaccard(text_nums, q_nums) if (text_nums or q_nums) else 0.0

        # 文本 n-gram
        q_ngrams = _char_ngrams(content, 2) | _char_ngrams(content, 3)
        text_score = _jaccard(text_ngrams, q_ngrams)

        # 选项结构
        q_has_opts = _has_options(content)
        opts_score = 0.15 if (text_has_opts and q_has_opts) else 0.0

        # 综合得分：数字指纹权重最高（数学题几乎靠数字就能定位）
        # 文本 n-gram 次之，选项结构小加分
        combined = min(
            1.0,
            fp_score * 0.55 + text_score * 0.35 + opts_score * 0.10,
        )

        reasons: List[str] = []
        if fp_score >= 0.6:
            reasons.append(f"数字匹配({len(text_nums & q_nums)}个)")
        if text_score >= 0.25:
            reasons.append(f"文本相似({text_score:.0%})")
        if opts_score > 0:
            reasons.append("同为选择题")

        if combined < 0.15:
            continue

        scored.append(
            BankMatchCandidate(
                question_id=qid,
                bank_id=bank_id,
                bank_title=bank_title,
                content=content[:80] + ("..." if len(content) > 80 else ""),
                knowledge_point=kp,
                score=round(combined, 3),
                text_score=round(text_score, 3),
                fingerprint_score=round(fp_score, 3),
                options_score=round(opts_score, 3),
                match_reasons=reasons,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


# ============ 知识点匹配 ============

def match_knowledge_points(
    text: str,
    subject: str,
    db_kps: List[Tuple[int, str, str]],  # (kp_id, name, subject)
    top_k: int = 5,
) -> List[KPMatchCandidate]:
    """对一段错题文本，从候选知识点中找最相关的知识点。

    db_kps 由调用方按 subject 预过滤后传入。
    """
    if not text or not db_kps:
        return []

    text_ngrams2 = _char_ngrams(text, 2)
    text_ngrams3 = _char_ngrams(text, 3)
    text_lower = text.lower()

    scored: List[KPMatchCandidate] = []
    for kp_id, name, kp_subject in db_kps:
        reasons: List[str] = []
        score = 0.0

        # 精确子串命中（最强信号）
        if name in text:
            score = 0.95
            reasons.append("精确命中")
        else:
            # n-gram 重叠
            name_ngrams2 = _char_ngrams(name, 2)
            name_ngrams3 = _char_ngrams(name, 3)
            j2 = _jaccard(text_ngrams2, name_ngrams2)
            j3 = _jaccard(text_ngrams3, name_ngrams3)
            text_score = max(j2, j3)

            # 关键词加权：KP 名称的每个字在文本中出现次数
            keyword_hits = sum(1 for ch in name if ch in text_lower)
            keyword_ratio = keyword_hits / len(name) if name else 0

            score = min(0.85, text_score * 0.6 + keyword_ratio * 0.4)

            if text_score >= 0.2:
                reasons.append(f"关键词匹配({text_score:.0%})")
            if keyword_ratio >= 0.5:
                reasons.append("关键词覆盖")

        if score < 0.2:
            continue

        scored.append(
            KPMatchCandidate(
                knowledge_point_id=kp_id,
                name=name,
                subject=kp_subject,
                score=round(score, 3),
                match_reasons=reasons,
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_k]


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"
