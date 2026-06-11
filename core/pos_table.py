from __future__ import annotations

POS_TO_RULE: dict[str, str] = {
    "조사": "제41항",
    "어미": "제41항",
    "의존 명사": "제42항",
    "단위명사": "제43항",
    "수사": "제44항",
    "보조 동사": "제47항",
    "보조 형용사": "제47항",
    "고유 명사": "제48항",
    "전문 용어": "제50항",
    "명사": "제2항",
    "접사": "접사(붙임)",
}

ABBREV_TO_POS: dict[str, str] = {
    "명": "명사",
    "관": "관형사",
    "부": "부사",
    "감": "감탄사",
    "대": "대명사",
    "수": "수사",
    "동": "동사",
    "형": "형용사",
    "조": "조사",
}

ENUMERATION_WORDS: set[str] = {
    "겸",
    "내지",
    "대",
    "및",
    "등",
    "등등",
    "등속",
    "등지",
    "따위",
}

HOMOGRAPH_42_WORDS: set[str] = {"뿐", "대로", "만큼", "만", "지", "차", "들", "판"}


def normalize_pos(pos: str) -> str:
    return " ".join(pos.strip().split())


def split_compound_pos(pos: str) -> list[str]:
    normalized = normalize_pos(pos)
    return [part.strip() for part in normalized.split("·") if part.strip()]


def map_pos(pos: str) -> str | None:
    normalized = normalize_pos(pos)
    normalized = ABBREV_TO_POS.get(normalized, normalized)
    return POS_TO_RULE.get(normalized)


def map_pos_all(pos: str) -> list[str]:
    rules: list[str] = []
    for part in split_compound_pos(pos):
        rule = map_pos(part)
        if rule and rule not in rules:
            rules.append(rule)
    return rules


def is_enumeration(word: str) -> bool:
    return word in ENUMERATION_WORDS


def is_homograph_42(word: str) -> bool:
    return word in HOMOGRAPH_42_WORDS
