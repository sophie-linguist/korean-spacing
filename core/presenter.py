from __future__ import annotations

from collections import defaultdict
from typing import Any

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
    return "사전 확인"


def _to_entry(item: dict[str, Any]) -> Entry:
    return Entry(
        word=item.get("word_raw") or "",
        pos=item.get("pos") or "",
        definition=item.get("definition") or "",
        type=item.get("type") or "",
        cat=item.get("cat"),
        group_code=item.get("group_code"),
        spacing_badge=_spacing_badge(item.get("pos") or ""),
        target_code=item.get("target_code"),
    )


def _fold_senses(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    grouped: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[item.get("group_code")].append(item)

    selected: list[dict[str, Any]] = []
    notes: list[str] = []
    for group_code, group_items in grouped.items():
        selected.extend(group_items[:3])
        if len(group_items) > 3:
            notes.append(f"group {group_code}: 외 {len(group_items)-3}개 뜻")
    return selected, notes


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
