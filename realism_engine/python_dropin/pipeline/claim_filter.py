"""
Optional reference module for claim safety checks.

This is intentionally simple. Claude can adapt it into the repo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ClaimGrade(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class ClaimCheck:
    claim: str
    grade: ClaimGrade
    reason: str
    safe_rewrite: str


RED_PATTERNS = [
    r"guarantee",
    r"guaranteed",
    r"top\s*3",
    r"map\s*pack.*guarantee",
    r"70%",
    r"80%",
    r"dominate google",
    r"will get more leads",
    r"will increase revenue",
    r"google will show",
    r"invisible to most",
    r"exactly what.*costing",
]

YELLOW_PATTERNS = [
    r"costing you customers",
    r"losing customers",
    r"handing customers",
    r"competitors are getting",
    r"i can fix it",
    r"google is.*punishing",
]


def quick_claim_check(claim: str) -> ClaimCheck:
    c = claim.lower()
    for pat in RED_PATTERNS:
        if re.search(pat, c):
            return ClaimCheck(
                claim=claim,
                grade=ClaimGrade.RED,
                reason="Contains a guarantee, unsupported statistic, or unproven SEO/result claim.",
                safe_rewrite="I can help improve the controllable factors that make the business more competitive online.",
            )
    for pat in YELLOW_PATTERNS:
        if re.search(pat, c):
            return ClaimCheck(
                claim=claim,
                grade=ClaimGrade.YELLOW,
                reason="Directionally possible, but too strong without evidence.",
                safe_rewrite="This may be making people less likely to call or choose the business online.",
            )
    return ClaimCheck(
        claim=claim,
        grade=ClaimGrade.GREEN,
        reason="No obvious guarantee or unsupported result claim found.",
        safe_rewrite=claim,
    )


def scan_script(script: str) -> list[ClaimCheck]:
    sentences = re.split(r"(?<=[.!?])\s+", script.strip())
    return [quick_claim_check(s) for s in sentences if s.strip()]
