"""이름 + 호칭어/관직명 탐지 — 제48항.

'성과 이름은 붙여 쓰고, 이에 덧붙는 호칭어·관직명 등은 띄어 쓴다.'
입력 끝에서 호칭어를 분리하고, 남은 부분이 한국 성씨로 시작하는
2~4음절 이름이면 제48항 안내를 생성한다.
"""

from __future__ import annotations

from core.schema import InspectResult, RuleHint

# 호칭어·관직명 (긴 것 우선)
_HONORIFICS: tuple[str, ...] = tuple(sorted([
    "대통령", "국무총리", "장관", "차관",
    "총장", "원장", "부장", "과장", "차장", "사장", "회장", "이사장", "위원장",
    "선생님", "선생", "교수", "박사", "의원",
    "장군", "대령", "중령", "소령", "대위", "중위", "소위",
    "사모님",
    "님", "씨", "군", "양",
], key=len, reverse=True))

# 한국 성씨 (인구 비율 상위 약 60개 + 2음절 성씨)
_SURNAMES_1: frozenset[str] = frozenset(
    "김이박최정강조윤장임한오서신권황안송류유전홍고문양손배백허노남하주우곽성차방"
    "진심위추엄원천변공구모민우탁연방육야마봉사반선설빈"
)
_SURNAMES_2: frozenset[str] = frozenset([
    "남궁", "독고", "황보", "사공", "선우", "제갈", "동방",
])


def _is_korean_name(text: str) -> bool:
    """성씨로 시작하는 2~4음절 한국 이름인지 판정."""
    if not (2 <= len(text) <= 4):
        return False
    if text[:2] in _SURNAMES_2:
        return True
    if text[0] in _SURNAMES_1:
        return True
    return False


def detect_honorific(text: str, db_path: str | None = None) -> InspectResult | None:
    """입력이 '이름 + 호칭어'이면 제48항 안내를 만든다."""
    joined = "".join(text.strip().split())
    if not joined:
        return None

    for h in _HONORIFICS:
        if not joined.endswith(h) or len(joined) <= len(h):
            continue

        name = joined[: -len(h)]
        if not _is_korean_name(name):
            continue

        spaced = f"{name} {h}"
        rule = RuleHint(
            항번호="제48항",
            원칙허용="띄움",
            요지=f"성과 이름은 붙여 쓰고, 호칭어·관직명은 띄어 씁니다 — '{name}' + '{h}' → '{spaced}'.",
        )
        return InspectResult(
            input=text,
            found=True,
            rule_hints=[rule],
            spacing_options=[spaced],
            notes=[
                f"'{name}'은(는) 성명, '{h}'은(는) 호칭어/관직명으로 보입니다.",
                "성명은 붙여 쓰고 호칭어·관직명은 띄어 씁니다(제48항).",
            ],
        )

    return None
