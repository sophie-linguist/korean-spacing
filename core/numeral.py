"""수 띄어쓰기 — 제43항(수 + 단위 명사)과 제44항(만 단위 띄어쓰기).

형태소 분석기 없이 닫힌 형태소 집합 + 결정적 규칙으로 처리한다.

  - 제43항: 입력 끝에서 단위 명사를 떼고, 그 앞이 수 표현(고유어/한자어)이면
    '수 + 단위'로 보고 띄어 씀(원칙)/붙여 씀(숫자 뒤 허용)을 안내한다.
  - 제44항: 입력 전체가 한자어 수이고 '만·억·조' 자리가 있으면 만 단위로 띄운다.

안전 원칙: **단위 바로 앞에 실제 수가 있을 때만** 인식한다(번호 게이트).
'운명·시대'처럼 단위 글자로 끝나도 앞이 수가 아니면 침묵하므로 일반어 오탐이 적다.
"""

from __future__ import annotations

from core.schema import InspectResult, RuleHint

# 고유어 수 (관형사형 포함). 단위 앞에서는 '셋→세', '넷→네'처럼 관형사형이 쓰인다.
# '서/너'(서 돈·너 말)는 매우 드물고 '도서·서원' 등과 충돌이 잦아 제외한다.
_NATIVE_ONES = (
    "하나", "한", "둘", "두", "셋", "세", "석", "넷", "네", "넉",
    "다섯", "여섯", "일곱", "여덟", "아홉",
)
_NATIVE_TENS = ("열", "스물", "서른", "마흔", "쉰", "예순", "일흔", "여든", "아흔")
# 단위 앞에서 형태가 바뀌는 고유어 수(단독으로 쓰일 때만).
_NATIVE_BEFORE_UNIT = {"스물": "스무"}

# 한자어 수 형태소(+아라비아 숫자).
_SINO_CHARS = set("영공일이삼사오육칠팔구십백천만억조경") | set("0123456789")
_MAN_UNITS = set("만억조경")

# 단위 명사(닫힌 목록). 앞에 수가 있을 때만 인식하므로 비교적 넓혀도 안전하다.
# '관·자·되·말·섬·돈·냥·단·건' 등 옛 단위나 흔한 단어와 충돌이 잦은 글자는 제외한다.
# 긴 단위가 짧은 단위에 먹히지 않도록 길이 역순으로 정렬해 쓴다.
_UNITS = (
    "센티미터", "킬로그램", "밀리미터", "퍼센트", "킬로미터",
    "개월", "차례", "바퀴", "갈래", "그루", "송이", "포기", "마리", "켤레", "자루",
    "그릇", "사발", "숟가락", "모금", "달러", "위안", "미터", "그램", "리터",
    "시간", "쌍", "축", "톳", "두름", "거리",
    "개", "대", "명", "권", "장", "벌", "잔", "병", "근", "채", "척", "칸",
    "번", "톤", "살", "줄", "통", "점",
    "원", "엔", "년", "주", "초", "평",
)
_UNITS_SORTED = tuple(sorted(set(_UNITS), key=len, reverse=True))


def _match_unit(joined: str) -> str | None:
    """입력 끝에 붙는 단위 명사 중 가장 긴 것을 돌려준다(앞말이 있어야 함)."""
    best: str | None = None
    for unit in _UNITS_SORTED:
        if joined.endswith(unit) and len(joined) > len(unit):
            if best is None or len(unit) > len(best):
                best = unit
    return best


def _is_native_number(s: str) -> bool:
    """s가 고유어 수(한·두·열두·스물한·아흔아홉 …)이면 True."""
    if not s:
        return False
    if s in _NATIVE_ONES:
        return True
    for tens in _NATIVE_TENS:
        if s == tens:
            return True
        if s.startswith(tens) and s[len(tens):] in _NATIVE_ONES:
            return True
    return False


def _is_sino_number(s: str) -> bool:
    """s가 한자어 수/아라비아 숫자 글자로만 이루어졌으면 True."""
    return bool(s) and all(ch in _SINO_CHARS for ch in s)


def _peel_number(s: str) -> tuple[str, str] | None:
    """s 끝에서 가장 긴 수 표현 접미사를 떼어 (앞부분, 수)를 돌려준다. 없으면 None."""
    for i in range(len(s)):
        cand = s[i:]
        if _is_native_number(cand) or _is_sino_number(cand):
            return s[:i], cand
    return None


def _space_man_units(num: str) -> str:
    """한자어 수에서 '만·억·조·경' 뒤에 내용이 더 있으면 띄운다(제44항)."""
    out: list[str] = []
    for i, ch in enumerate(num):
        out.append(ch)
        if ch in _MAN_UNITS and i + 1 < len(num):
            out.append(" ")
    return "".join(out)


def _unit_result(text: str, prefix: str, num: str, unit: str) -> InspectResult:
    spaced_num = _space_man_units(num)
    show_num = _NATIVE_BEFORE_UNIT.get(spaced_num, spaced_num)
    spaced = " ".join(filter(None, [prefix, show_num, unit]))
    joined_unit = " ".join(filter(None, [prefix, show_num + unit]))
    rule43 = RuleHint(
        항번호="제43항",
        원칙허용="원칙+허용",
        요지="단위를 나타내는 명사는 띄어 씀이 원칙이며, 숫자나 수 관형사 뒤에서는 붙여 쓸 수 있습니다.",
    )
    rules = [rule43]
    note = f"수 ‘{show_num}’와(과) 단위 ‘{unit}’의 결합으로 보아 제43항을 안내합니다."
    # 수 부분에 만 단위 경계가 있어 띄어졌으면(삼천이백억 오천만 원) 제44항도 함께 적용된다.
    if spaced_num != num:
        rules.insert(
            0,
            RuleHint(
                항번호="제44항",
                원칙허용="원칙",
                요지="수를 적을 때에는 ‘만, 억, 조’ 단위로 띄어 씁니다.",
            ),
        )
        note = (
            f"수 ‘{show_num}’는 만 단위로 띄우고(제44항), 단위 ‘{unit}’은(는) "
            f"앞말과 띄어 씁니다(제43항)."
        )
    return InspectResult(
        input=text,
        found=True,
        rule_hints=rules,
        spacing_options=list(dict.fromkeys([spaced, joined_unit])),
        notes=[note],
    )


def _big_number_result(text: str, joined: str, spaced: str) -> InspectResult:
    rule = RuleHint(
        항번호="제44항",
        원칙허용="원칙",
        요지="수를 적을 때에는 ‘만, 억, 조’ 단위로 띄어 씁니다.",
    )
    return InspectResult(
        input=text,
        found=True,
        rule_hints=[rule],
        spacing_options=list(dict.fromkeys([spaced, joined])),
        notes=[f"큰 수는 만 단위로 끊어 띄어 씁니다: ‘{spaced}’."],
    )


def _big_number_ok_result(text: str, joined: str) -> InspectResult:
    """이미 만 단위로 바르게 적힌 큰 수에 대한 긍정 확인(침묵 대신).

    '삼천이백억'처럼 만/억/조 자리가 맨 끝에 있어 더 띄어 쓸 곳이 없는 경우,
    바꿀 게 없다고 침묵하면 '처리 못 함'으로 오해되므로 '이대로 맞다'고 알려 준다.
    """
    rule = RuleHint(
        항번호="제44항",
        원칙허용="확인",
        요지="‘만, 억, 조’ 단위로 끊어 띄어 쓰는데, 이 수는 이미 바르게 적혀 더 띄어 쓸 곳이 없습니다.",
    )
    return InspectResult(
        input=text,
        found=True,
        rule_hints=[rule],
        spacing_options=[joined],
        notes=[f"‘{joined}’은(는) 이미 만 단위로 바르게 적혔습니다. 그대로 쓰면 됩니다."],
    )


def _number_is_strong(num: str) -> bool:
    """오탐 억제용: 고유어 수이거나 2글자 이상이면 '강한' 수로 본다.

    '사장·공장'처럼 단일 한자 숫자(사=4, 공=0)로 시작하는 일반어가 사전 풀이에
    '수 + 단위'(사 장)로 끼어드는 것을 막는다.
    """
    return _is_native_number(num) or len(num) >= 2


def detect_numeral(
    text: str, db_path: str | None = None, strong_only: bool = False
) -> InspectResult | None:
    """입력이 '수 + 단위'(제43항)이거나 큰 한자어 수(제44항)이면 안내를 만든다.

    strong_only=True이면 단일 한자 숫자만으로 이루어진 약한 수는 무시한다
    (사전 등재어에 병행 안내를 덧붙일 때 오탐을 줄이기 위함).
    """
    joined = "".join(text.strip().split())
    if not joined:
        return None

    unit = _match_unit(joined)
    if unit is not None:
        peeled = _peel_number(joined[: -len(unit)])
        if peeled is not None:
            prefix, num = peeled
            if not strong_only or _number_is_strong(num):
                return _unit_result(text, prefix, num, unit)

    if _is_sino_number(joined):
        spaced = _space_man_units(joined)
        if spaced != joined:
            return _big_number_result(text, joined, spaced)
        # 만 단위가 맨 끝에 있어 띄울 곳이 없는 큰 수('삼천이백억')는 침묵 대신 긍정 확인.
        # strong_only(사전 등재어 병행 안내)일 때는 확인 노트가 군더더기이므로 제외한다.
        if not strong_only and len(joined) >= 2 and any(ch in _MAN_UNITS for ch in joined):
            return _big_number_ok_result(text, joined)

    return None
