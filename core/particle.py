"""조사 분리 탐지 — 제41항 '조사는 그 앞말에 붙여 쓴다.'

입력 끝에서 조사를 반복 분리하여, 남은 부분이 사전에 등재된 단어이면
'체언 + 조사 연쇄 → 붙여 씀(제41항)' 안내를 생성한다.

조사 목록은 우리말샘 dict.db에서 품사='조사'인 항목을 기반으로 하되,
고빈도 조사를 닫힌 목록으로 내장해 DB 없이도 동작한다.
긴 조사부터 매칭하여 '에서' vs '서' 같은 부분 매칭 오류를 방지한다.
"""

from __future__ import annotations

from core.local_index import lookup
from core.schema import InspectResult, RuleHint

# 고빈도 조사 닫힌 목록 (긴 것 우선 매칭을 위해 길이 역순 정렬)
_PARTICLES: tuple[str, ...] = tuple(sorted([
    # 2음절+
    "에서부터", "으로부터", "으로서", "으로써", "에서", "부터",
    "까지", "처럼", "만큼", "마저", "밖에", "조차",
    "에게", "한테", "더러", "보고",
    "으로", "이나마", "이라도", "이든지", "이야말로",
    "나마", "라도", "든지",
    "이나", "이란", "이며", "이고", "이라",
    # 1음절
    "은", "는", "이", "가", "을", "를",
    "의", "에", "도", "만", "나", "야",
    "로", "와", "과", "랑",
], key=len, reverse=True))


def _strip_particles(text: str) -> list[str] | None:
    """끝에서 조사를 반복 분리해 [잔여, 조사1, 조사2, ...] 를 돌려준다.

    분리할 조사가 없으면 None.
    """
    remaining = text
    found: list[str] = []

    while remaining:
        matched = False
        for p in _PARTICLES:
            if remaining.endswith(p) and len(remaining) > len(p):
                found.append(p)
                remaining = remaining[: -len(p)]
                matched = True
                break
        if not matched:
            break

    if not found:
        return None
    return [remaining, *reversed(found)]


def detect_particle_chain(text: str, db_path: str | None = None) -> InspectResult | None:
    """입력이 '체언 + 조사 연쇄'이면 제41항 안내를 만든다."""
    joined = "".join(text.strip().split())
    parts = _strip_particles(joined)
    if parts is None or len(parts) < 2:
        return None

    root = parts[0]
    particles = parts[1:]

    # 잔여(root)가 사전에 등재된 단어인지 확인
    entries = lookup(root, db_path)
    if not entries:
        return None

    particle_str = " + ".join(particles)
    display = root + "".join(particles)

    rule = RuleHint(
        항번호="제41항",
        원칙허용="붙임",
        요지=f"조사는 앞말에 붙여 씁니다. '{root}' + {particle_str} → 붙여 씀이 맞습니다.",
    )
    return InspectResult(
        input=text,
        found=True,
        rule_hints=[rule],
        spacing_options=[display],
        notes=[
            f"'{root}'에 조사 '{particle_str}'이(가) 결합한 형태입니다.",
            "조사가 둘 이상 연속되어도 앞말에 붙여 씁니다(제41항).",
        ],
    )
