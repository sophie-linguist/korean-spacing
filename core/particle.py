"""조사 분리 탐지 — 제41항 '조사는 그 앞말에 붙여 쓴다.'

입력 끝에서 조사를 반복 분리하여, 남은 부분이 사전에 등재된 단어이면
'체언 + 조사 연쇄 → 붙여 씀(제41항)' 안내를 생성한다.

조사 목록은 우리말샘 dict.db에서 품사='조사'인 항목을 기반으로 하되,
고빈도 조사를 닫힌 목록으로 내장해 DB 없이도 동작한다.
긴 조사부터 매칭하여 '에서' vs '서' 같은 부분 매칭 오류를 방지한다.
"""

from __future__ import annotations

from core.local_index import lookup
from core.presenter import make_component_entry
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


def _peel_to_registered_root(
    joined: str, db_path: str | None
) -> tuple[str, list[str]] | None:
    """끝에서 조사를 하나씩 떼되, 남은 부분이 사전 등재어가 되는 '가장 긴 어근'에서 멈춘다.

    '하나도'는 '도'만 떼면 '하나'(등재어)가 되므로 거기서 멈춘다(→ '하'+'나'+'도' 과분해 방지).
    반환: (어근, [조사…]) 또는 None.
    """
    remaining = joined
    peeled: list[str] = []  # 뗀 순서(끝 조사부터)
    while True:
        if peeled and lookup(remaining, db_path):
            return remaining, list(reversed(peeled))
        for p in _PARTICLES:
            if remaining.endswith(p) and len(remaining) > len(p):
                peeled.append(p)
                remaining = remaining[: -len(p)]
                break
        else:
            return None


def detect_particle_chain(text: str, db_path: str | None = None) -> InspectResult | None:
    """입력이 '체언 + 조사 연쇄'이면 제41항 안내를 만든다."""
    joined = "".join(text.strip().split())
    peeled = _peel_to_registered_root(joined, db_path)
    if peeled is None:
        return None

    root, particles = peeled
    if not particles:
        return None

    # 잔여(root)가 사전에 등재된 단어인지 확인(가장 긴 어근에서 이미 확인됨)
    entries = lookup(root, db_path)
    if not entries:
        return None

    particle_str = " + ".join(particles)
    display = root + "".join(particles)

    # 구성요소 사전 정보: 앞말(체언) + 조사들.
    component_entries = []
    root_entry = make_component_entry(
        root, prefer=("대명사", "명사", "수사"), role="앞말(체언)", db_path=db_path
    )
    if root_entry is not None:
        component_entries.append(root_entry)
    for p in particles:
        pe = make_component_entry(p, prefer=("조사",), role="조사", db_path=db_path)
        if pe is not None:
            component_entries.append(pe)

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
        entries=component_entries,
        notes=[
            f"'{root}'에 조사 '{particle_str}'이(가) 결합한 형태입니다.",
            "조사가 둘 이상 연속되어도 앞말에 붙여 씁니다(제41항).",
        ],
    )
