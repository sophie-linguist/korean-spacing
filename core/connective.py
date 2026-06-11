"""제45항 — 두 말을 이어 주거나 열거하는 말은 띄어 쓴다.

'및·겸·대·내지·또는·혹은'(이어 줌)과 '등·등등·등지'(열거)는 앞뒤를 띄어 쓴다.
이 검출기는 입력의 어절 경계를 살려, 이런 연결어가 끼면 제45항을 안내하고
**합성어로 붙이지 않도록** 한다('이사장 및 이사' → '이사장및이사' 오류 방지).

핵심 안전 원칙: '등·대'는 일반 단어 속에도 흔히 나타나므로(평등·시대) 붙은 입력에서
substring으로 찾지 않는다. 어절로 분리돼 가운데/끝에 단독으로 올 때만 인정한다.
다만 '및·내지'는 단어 안에 거의 나타나지 않아 붙은 입력에서도 안전하게 가른다.
"""

from __future__ import annotations

from core.schema import InspectResult, RuleHint

# 두 말을 이어 주는 말(가운데에 단독으로 옴).
_CONNECT_MID = ("및", "겸", "대", "내지", "또는", "혹은")
# 열거 뒤에 오는 말(끝에 단독으로 옴).
_CONNECT_END = ("등", "등등", "등지")
# 붙은 입력에서도 안전하게 가를 수 있는 말(단어 속에 거의 안 나타남).
_SAFE_JOINED = ("및", "내지")

_RULE = RuleHint(
    항번호="제45항",
    원칙허용="원칙",
    요지="두 말을 이어 주거나 열거할 때 쓰는 ‘및·겸·대·내지·등’ 등은 앞말과 띄어 씁니다.",
)


def _result(text: str, spaced: str, word: str) -> InspectResult:
    return InspectResult(
        input=text,
        found=True,
        rule_hints=[_RULE],
        spacing_options=[spaced],
        notes=[
            f"‘{word}’은(는) 두 말을 이어 주거나 열거하는 말이라 앞뒤를 띄어 씁니다(제45항).",
            "이 도구는 한 단어·짧은 표현에 맞춰져 있어, 연결어로 묶인 표현은 띄어쓰기만 확인합니다.",
        ],
    )


def detect_connective(text: str) -> InspectResult | None:
    """입력이 연결어·열거어를 포함하면 제45항(띄어 씀)을 안내한다."""
    tokens = text.split()

    # 어절로 분리된 경우: 가운데의 이어 주는 말 / 끝의 열거 말.
    if len(tokens) >= 2:
        for tok in tokens[1:-1]:
            if tok in _CONNECT_MID:
                return _result(text, " ".join(tokens), tok)
        if tokens[-1] in _CONNECT_END:
            return _result(text, " ".join(tokens), tokens[-1])

    # 붙여 쓴 경우: '및·내지'만 안전하게 가른다.
    joined = "".join(tokens)
    for word in _SAFE_JOINED:
        idx = joined.find(word)
        if 0 < idx < len(joined) - len(word):
            spaced = f"{joined[:idx]} {word} {joined[idx + len(word):]}"
            return _result(text, spaced, word)

    return None
