"""접두사 + 자립 명사 인식 — 접사는 단어가 아니라 어근에 붙는 형태소라 붙여 쓴다.

'본구축'처럼 사전에 한 단어로 없지만 '접두사(본-) + 자립 명사(구축)'로 분석되는 붙여 쓴
입력을 인식해 붙여 씀('본구축')을 안내한다. 관형사 + 명사(한잎 → 한 잎, 띄움)와 달리
접사는 자립어가 아니므로 붙는다.

정밀도 장치(다른 detector와 같은 원칙: 사전 자기검증):
- 접두사는 우리말샘에 'pos=접사 + word_raw가 -로 끝남'(어두 접사)으로 등재된 것만 인정한다.
- 뒤는 자립 명사(의존 명사 제외)로 등재된 것만 인정한다.
- '본·맨'처럼 접두사이면서 관형사로도 쓰이는 글자는 뜻에 따라 붙임/띄움이 갈리므로,
  단정하지 않고 두 해석('본계약' vs '본 계약')을 함께 제시한다(동형이의 처리 원칙).
- cascade에서 detect_adnominal_noun(한·새·첫… 관형사 목록) '뒤'에 두어, 그 목록이 이미
  처리하는 입력은 종전 동작(띄움)을 유지하고, 그 밖의 접두사만 이 detector가 맡는다.
"""

from __future__ import annotations

from core.local_index import get_connection, normalize_lookup_forms
from core.presenter import make_component_entry
from core.schema import InspectResult, RuleHint


def _is_prefix(word: str, db_path: str | None) -> bool:
    """우리말샘에 어두 접사(접두사)로 등재돼 있는지(word_raw가 '-'로 끝남)."""
    joined, _ = normalize_lookup_forms(word)
    con = get_connection(db_path)
    row = con.execute(
        "SELECT 1 FROM entries WHERE word_joined = ? "
        "AND pos = '접사' AND word_raw LIKE '%-' LIMIT 1",
        (joined,),
    ).fetchone()
    return row is not None


def _is_determiner(word: str, db_path: str | None) -> bool:
    """관형사로도 등재돼 있는지(접두사/관형사 양쪽이면 붙임/띄움이 갈리므로 제외)."""
    joined, _ = normalize_lookup_forms(word)
    con = get_connection(db_path)
    row = con.execute(
        "SELECT 1 FROM entries WHERE word_joined = ? AND pos LIKE '%관형사%' LIMIT 1",
        (joined,),
    ).fetchone()
    return row is not None


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


def detect_prefix(text: str, db_path: str | None = None) -> InspectResult | None:
    """'접두사 + 자립 명사'(예: 본구축 → 본+구축)를 인식해 붙여 씀을 안내한다. 아니면 None."""
    joined = "".join(text.strip().split())
    if len(joined) < 2:
        return None

    # 가장 긴 접두사부터 시도한다(접두사는 대개 1~2음절).
    for length in range(len(joined) - 1, 0, -1):
        prefix, rest = joined[:length], joined[length:]
        if not _is_prefix(prefix, db_path):
            continue
        if not _is_free_noun(rest, db_path):
            continue

        spaced = f"{prefix} {rest}"
        rules = [
            RuleHint(
                항번호="제2항",
                원칙허용="붙임",
                요지="접사는 단어가 아니라 어근에 붙는 형태소이므로 앞말에 붙여 씁니다.",
            )
        ]
        options = [joined]
        notes = [f"‘{prefix}-’(접두사) + ‘{rest}’(명사)로 보면 붙여 씁니다: ‘{joined}’."]

        # 접두사이면서 관형사로도 쓰이는 글자(본·맨…)는 뜻이 갈리므로 띄움도 함께 보인다.
        if _is_determiner(prefix, db_path):
            rules.append(
                RuleHint(
                    항번호="제2항",
                    원칙허용="띄움",
                    요지="관형사는 뒤따르는 체언과 띄어 씁니다.",
                )
            )
            options.append(spaced)
            notes.append(
                f"다만 ‘{prefix}’을(를) 관형사로 보면 ‘{spaced}’처럼 띄어 씁니다(뜻이 갈립니다)."
            )

        entries = []
        pre_entry = make_component_entry(prefix, prefer=("접사",), role="접두사", db_path=db_path)
        if pre_entry is not None:
            entries.append(pre_entry)
        noun_entry = make_component_entry(rest, prefer=("명사",), role="명사", db_path=db_path)
        if noun_entry is not None:
            entries.append(noun_entry)

        return InspectResult(
            input=text,
            found=True,
            rule_hints=rules,
            spacing_options=options,
            entries=entries,
            notes=notes,
        )

    return None
