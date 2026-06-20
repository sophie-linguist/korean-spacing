"""관형사 + 명사 인식 — 제2항 '문장의 각 단어는 띄어 씀을 원칙으로 한다.'

'한잎'처럼 사전에 한 단어로 없지만 '관형사(한) + 명사(잎)'로 분석되는 붙여 쓴 입력을
인식해 띄어 씀(한 잎)을 안내한다. 의존 명사 결합(한 것)과 달리 뒤가 자립 명사이므로
용언 활용형 게이트가 아니라 '관형사 접두 + 자립 명사' 조건으로 판정한다.
"""

from __future__ import annotations

from core.local_index import get_connection, normalize_lookup_forms
from core.presenter import make_component_entry
from core.schema import InspectResult, RuleHint

# 흔한 관형사(수·지시·성상). 긴 것 우선 매칭.
# 모호한 1음절 관형사(너·서·석·닷·각·매 등 다른 품사와 겹침이 큰 것)는
# 오인을 줄이기 위해 제외하고, 비교적 분명한 관형사만 둔다.
# 지시관형사 '이·그·저'는 포함한다: '이것·그분·저혈압·저위험'처럼 굳어진 합성어·파생어는
# cascade 3단계(사전 조회)에서 먼저 붙임으로 처리·보호되므로, adnoun까지 내려오는 건
# 사전에 없는 '이/그/저 + 자립명사'(= 진짜 지시 구절: 이 사람, 저 건물)뿐이라 띄움이 옳다.
_DETERMINERS = (
    "다섯", "여섯", "일곱", "여덟", "아홉", "스무", "온갖", "갖은", "여러",
    "모든", "어느", "무슨", "이런", "그런", "저런", "다른", "어떤",
    "한", "두", "세", "네", "열", "몇", "새", "헌", "옛", "첫", "온갖", "웬",
    "이", "그", "저",
)


def _is_free_noun(word: str, db_path: str | None) -> bool:
    """자립 명사(의존 명사 제외)로 등재돼 있는지."""
    joined, _ = normalize_lookup_forms(word)
    con = get_connection(db_path)
    row = con.execute(
        "SELECT 1 FROM entries WHERE word_joined = ? "
        "AND pos LIKE '%명사%' AND pos NOT LIKE '%의존%' LIMIT 1",
        (joined,),
    ).fetchone()
    return row is not None


def detect_adnominal_noun(text: str, db_path: str | None = None) -> InspectResult | None:
    """'관형사 + 자립 명사'(예: 한잎 → 한 잎)를 인식해 제2항을 안내한다. 아니면 None."""
    joined = "".join(text.strip().split())

    det = None
    for d in sorted(_DETERMINERS, key=len, reverse=True):
        if joined.startswith(d) and len(joined) > len(d):
            det = d
            break
    if det is None:
        return None

    noun = joined[len(det):]
    if not _is_free_noun(noun, db_path):
        return None

    spaced = f"{det} {noun}"
    rule = RuleHint(
        항번호="제2항",
        원칙허용="띄움",
        요지="관형사는 뒤따르는 체언과 띄어 씁니다.",
    )
    entries = []
    det_entry = make_component_entry(det, prefer=("관형사",), role="관형사", db_path=db_path)
    if det_entry is not None:
        entries.append(det_entry)
    noun_entry = make_component_entry(noun, prefer=("명사",), role="명사", db_path=db_path)
    if noun_entry is not None:
        entries.append(noun_entry)

    return InspectResult(
        input=text,
        found=True,
        rule_hints=[rule],
        spacing_options=[spaced],
        entries=entries,
        notes=[f"‘{det}’(관형사) + ‘{noun}’(명사)로 분석되어 띄어 씁니다(제2항)."],
    )
