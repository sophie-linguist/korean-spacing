from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CaretHint:
    rule: str
    policy: str
    options: list[str]
    message: str


def _spacing_options(word_raw: str) -> list[str]:
    spaced = " ".join(word_raw.replace("^", " ").split())
    joined = word_raw.replace("^", "")
    if spaced == joined:
        return [spaced]
    return [spaced, joined]


def caret_hint(word_raw: str, cat: str | None) -> CaretHint:
    options = _spacing_options(word_raw)
    has_cat = isinstance(cat, str) and bool(cat.strip())

    if has_cat:
        rule = "제50항"
        policy = "원칙+허용"
    else:
        rule = "제2항"
        policy = "원칙+허용"

    message = f"이 표현은 '{options[0]}'(원칙)과 '{options[-1]}'(허용)처럼 둘 다 사용할 수 있습니다."
    return CaretHint(rule=rule, policy=policy, options=options, message=message)


def caret_hint_from_joined(joined_input: str, word_raw: str, cat: str | None) -> CaretHint:
    _ = joined_input
    return caret_hint(word_raw=word_raw, cat=cat)
