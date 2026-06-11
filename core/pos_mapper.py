from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.pos_table import is_enumeration, map_pos_all, split_compound_pos

UNIT_KEYWORDS = (
    "세는 단위",
    "부피의 단위",
    "밀도를 나타내는 단위",
    "단위",
)


@dataclass(slots=True)
class MappedRule:
    항번호: str
    원칙허용: str
    요지: str


@lru_cache(maxsize=1)
def load_rules() -> dict[str, dict[str, Any]]:
    path = Path(__file__).with_name("rules_data.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {clause["항번호"]: clause for clause in data.get("조항", [])}


def _contains_unit_keyword(definition: str) -> bool:
    return any(keyword in definition for keyword in UNIT_KEYWORDS)


def _to_rule(num: str) -> MappedRule:
    clause = load_rules().get(num)
    if clause is None:
        return MappedRule(항번호=num, 원칙허용="원칙", 요지="")
    return MappedRule(
        항번호=num,
        원칙허용=clause.get("원칙허용", "원칙"),
        요지=clause.get("조항", ""),
    )


def map_entry(pos: str, definition: str, word: str | None = None) -> list[MappedRule]:
    rules: list[str] = []

    for num in map_pos_all(pos):
        if num not in rules:
            rules.append(num)

    parts = split_compound_pos(pos)
    has_dep_noun = "의존 명사" in parts or pos.strip() == "의존 명사"
    if has_dep_noun and _contains_unit_keyword(definition):
        if "제43항" not in rules:
            rules.append("제43항")

    if word and is_enumeration(word):
        if "제45항" not in rules:
            rules.append("제45항")

    return [_to_rule(num) for num in rules]
