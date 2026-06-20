from __future__ import annotations

from typing import Any

from core.local_index import lookup
from core.pos_table import HOMOGRAPH_42_WORDS
from core.schema import Entry, InspectResult

GENERAL_TYPE = "일반어"


def _spacing_badge(pos: str) -> str:
    if pos == "조사":
        return "붙임"
    if pos == "의존 명사":
        return "띄움"
    if pos in {"보조 동사", "보조 형용사"}:
        return "원칙 띄움/허용 붙임"
    if pos == "접사":
        return "붙임"
    return ""  # 평범한 단어는 띄어쓰기 배지 없음


def _clean_word(word_raw: str) -> str:
    """우리말샘 표제어의 형태소 경계 표시를 제거한다(얼마-나 → 얼마나, 인공^지능 → 인공 지능)."""
    return word_raw.replace("-", "").replace("^", " ").strip()


def _to_entry(item: dict[str, Any]) -> Entry:
    return Entry(
        word=_clean_word(item.get("word_raw") or ""),
        pos=item.get("pos") or "",
        definition=item.get("definition") or "",
        type=item.get("type") or "",
        cat=item.get("cat"),
        group_code=item.get("group_code"),
        spacing_badge=_spacing_badge(item.get("pos") or ""),
        target_code=item.get("target_code"),
    )


def make_component_entry(
    word: str,
    prefer: tuple[str, ...] = (),
    role: str | None = None,
    base_word: str | None = None,
    db_path: str | None = None,
) -> Entry | None:
    """분해된 구성요소(조사/의존명사/본용언 등)를 사전 조회해 Entry 하나로 만든다.

    prefer에 담긴 품사 부분문자열 순서대로 표제어를 고르고, 없으면 첫 항목을 쓴다.
    base_word가 있으면 그 기본형으로 조회하되 화면에는 원래 표기(word)를 보인다.
    사전에 없으면 None.
    """
    lookup_key = base_word or word
    rows = lookup(lookup_key, db_path)
    if not rows:
        return None

    def _score(r: dict[str, Any]) -> tuple[int, int, int, int]:
        pos = r.get("pos") or ""
        pos_rank = next((i for i, sub in enumerate(prefer) if sub in pos), len(prefer))
        defn = (r.get("definition") or "")[:10]
        is_dialect = 1 if ("방언" in defn or "북한어" in defn or "옛말" in defn) else 0
        is_general = 0 if (r.get("type") or "") == GENERAL_TYPE else 1
        return (pos_rank, is_dialect, is_general, r.get("target_code") or 0)

    chosen = min(rows, key=_score)

    display = _clean_word(chosen.get("word_raw") or word)
    return Entry(
        word=display,
        pos=chosen.get("pos") or "",
        definition=chosen.get("definition") or "",
        type=chosen.get("type") or "",
        spacing_badge=_spacing_badge(chosen.get("pos") or ""),
        target_code=chosen.get("target_code"),
        role=role,
    )


def _fold_senses(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    # 한 표제어의 뜻을 임의로 잘라내면 사용자가 "전체가 안 나온다"고 느끼고,
    # 잘린 자리에 내부 group_code가 도움말로 새어 나간다. 사전 조회 결과는
    # 전부 보여 주는 것이 원칙이므로(판단은 사용자가 한다) 접지 않는다.
    return list(items), []


def present(entries: list[dict[str, Any]], query: str) -> InspectResult:
    sorted_entries = sorted(entries, key=lambda x: (0 if x.get("type") == GENERAL_TYPE else 1, x.get("target_code") or 0))
    folded_entries, fold_notes = _fold_senses(sorted_entries)

    display_mode = "pos_compressed" if len(query.strip()) == 1 and len(folded_entries) >= 3 else "normal"

    notes = [
        "판단은 사용자가 합니다.",
        "의미 번호는 중요도 순서가 아닙니다.",
        "문장의 각 단어는 띄어 씀을 원칙으로 합니다(제2항).",
    ]
    notes.extend(fold_notes)

    if query.strip() in HOMOGRAPH_42_WORDS:
        notes.append("제42항 동형이의 가능성이 있어 조사/의존 명사 양쪽을 함께 안내합니다.")

    return InspectResult(
        input=query,
        found=bool(entries),
        display_mode=display_mode,
        entries=[_to_entry(item) for item in folded_entries],
        notes=notes,
    )
