"""미등록 합성명사·전문용어·고유명사 인식 (제50항/제49항).

'인공지능위원회'처럼 사전 표제어가 아니지만, 구성 단어들은 사전에 있는 덩어리를
인식해 규정을 안내한다. 핵심 안전 원칙:

  - 인식(어떤 규정이 적용되나)은 사전으로 한다.
  - 정확한 단어 경계(분절)는 사전 최장일치로 신뢰할 수 없으므로(예: '만성골수성백혈병'
    → '만 성골 수성 백혈병' 오타일링), **고신뢰일 때만** 구성 예시를 보여 주고
    아니면 침묵한다("애매하면 침묵"). 붙임형(=입력)은 항상 확신 있게 제시한다.

형태소분석기 미사용. 정밀 분절이 필요하면 별도 fallback 레이어(2차)에서 다룬다.
"""

from __future__ import annotations

from core.local_index import get_connection, normalize_lookup_forms
from core.schema import InspectResult, RuleHint

# 기관·조직·전문/교육 단위 접미부. 끝에 붙으면 고유명사·전문용어일 가능성이 높다.
# (매칭은 _match_org_suffix가 가장 긴 것을 고르므로 나열 순서는 무관)
ORG_SUFFIXES = (
    "주식회사", "유한회사", "위원회", "협의회", "추진단", "대학교", "대학원",
    "연구원", "연구소", "박물관", "도서관", "사업소", "사업단", "양성과정",
    "교육과정", "재단", "협회", "학회", "본부", "센터", "과정", "사업",
    "정책", "제도", "학과", "학부", "공사", "공단", "대학", "학교", "병원",
    "은행", "교회", "성당",
    "청", "처", "원", "국", "부", "과", "팀", "실", "관", "소", "사", "단",
)

MIN_INPUT_LEN = 3       # 너무 짧은 입력은 합성어로 보지 않음
MIN_PIECE_LEN = 2       # 1음절 조각은 우연 매칭이 많아 분절 신뢰도에서 제외


def _noun_pieces(joined: str) -> tuple[dict[str, set[str | None]], dict[str, str]]:
    """입력의 모든 부분문자열 중 '명사로 쓰이는 표제어'를 조회한다.

    반환: ({조각: {전문분야...}}, {조각: 띄어쓴_표기}).
    일반 명사(pos에 '명사' 포함, 의존명사 제외)와 구(word_unit='구') 표제어를 포함한다.
    구는 '인공^지능'처럼 pos가 비어 있는 합성 표제어를 잡기 위함이다.
    조각 자체가 '^'(어절 경계)로 띄어 쓰는 합성 표제어면('나선^은하'→'나선 은하') 분절
    예시를 더 정확히 펼치기 위해 그 표기를 spaced_map에 함께 모은다(정상나선은하→정상 나선 은하).
    주의: word_spaced는 '^'와 '-'(접사 경계)를 모두 공백으로 바꿔 '위원-회'→'위원 회'처럼
    붙여 써야 할 것까지 띄우므로 쓰지 않는다. word_raw에서 '^'만 공백으로 펼친다.
    """
    n = len(joined)
    subs = {joined[i:j] for i in range(n) for j in range(i + 1, n + 1)}
    if not subs:
        return {}, {}

    placeholders = ",".join("?" * len(subs))
    con = get_connection()
    rows = con.execute(
        f"""
        SELECT word_joined, word_raw, cat FROM entries
        WHERE word_joined IN ({placeholders})
          AND (
              (pos LIKE '%명사%' AND pos NOT LIKE '%의존%')
              OR (word_unit = '구' AND (pos = '' OR pos IS NULL))
          )
        """,
        list(subs),
    ).fetchall()

    pieces: dict[str, set[str | None]] = {}
    spaced_map: dict[str, str] = {}
    for row in rows:
        wj = row["word_joined"]
        pieces.setdefault(wj, set()).add(row["cat"])
        if "^" in (row["word_raw"] or ""):
            # '-'(접사)는 붙이고 '^'(어절)만 띄운다.
            caret_spaced = row["word_raw"].replace("-", "").replace("^", " ").strip()
            if caret_spaced and caret_spaced != wj:
                spaced_map[wj] = caret_spaced
    return pieces, spaced_map


def _best_cover(joined: str, pieces: dict[str, set[str | None]]) -> list[str] | None:
    """조각들로 입력 전체를 덮는 최소 조각 수 분절. 1음절 조각은 배제. 없으면 None."""
    n = len(joined)
    best: list[tuple[int, list[str]]] = [(10**9, [])] * (n + 1)
    best[0] = (0, [])
    for i in range(n):
        if best[i][0] == 10**9:
            continue
        for j in range(i + MIN_PIECE_LEN, n + 1):
            piece = joined[i:j]
            if piece in pieces:
                cand = best[i][0] + 1
                if cand < best[j][0]:
                    best[j] = (cand, best[i][1] + [piece])
    return best[n][1] if best[n][0] < 10**9 else None


def _match_org_suffix(joined: str) -> str | None:
    """입력 끝에 붙는 접미부 중 가장 긴 것을 돌려준다(없으면 None)."""
    best: str | None = None
    for suffix in ORG_SUFFIXES:
        if joined.endswith(suffix) and len(joined) > len(suffix):
            if best is None or len(suffix) > len(best):
                best = suffix
    return best


def detect_compound(text: str, db_path: str | None = None) -> InspectResult | None:
    """미등록 합성명사/전문용어/고유명사를 인식해 제50/49항을 안내한다.

    트리거(둘 중 하나 이상):
      (A) 기관·조직 접미부로 끝남 → 고유명사/기관명(제49·50항)
      (B) ≥2개 사전 명사로 깔끔히 덮이고(모든 조각 ≥2음절) 전문분야가 하나 이상 → 전문용어(제50항)
    어느 쪽도 아니면 None(침묵).
    """
    joined, _ = normalize_lookup_forms(text)
    if len(joined) < MIN_INPUT_LEN:
        return None

    pieces, spaced_map = _noun_pieces(joined)
    cover = _best_cover(joined, pieces)
    clean_cover = cover if (cover and len(cover) >= 2) else None
    # 모든 조각이 전문 분야(cat)를 가질 때만 전문용어로 인정 → 무의미어 오탐 차단.
    has_specialized = bool(
        clean_cover and all(any(c for c in pieces.get(p, set())) for p in clean_cover)
    )
    org_suffix = _match_org_suffix(joined)

    # 트리거 판정
    if org_suffix is not None:
        rule = RuleHint(
            항번호="제50항",
            원칙허용="원칙+허용",
            요지="성명 이외의 고유 명사 및 전문 용어는 단어별로 띄어 씀이 원칙이고, 단위/전문어로 붙여 씀도 허용합니다(제49·50항).",
        )
        note = f"미등록어이지만 '{org_suffix}'(으)로 끝나 전문용어·고유명사로 추정됩니다. 제49·50항을 안내합니다."
    elif clean_cover and has_specialized:
        rule = RuleHint(
            항번호="제50항",
            원칙허용="원칙+허용",
            요지="전문 용어는 단어별로 띄어 씀이 원칙이고, 붙여 씀도 허용합니다.",
        )
        note = "미등록어이지만 사전 등재 단어들의 결합(전문 분야 포함)으로 보여 제50항을 안내합니다."
    else:
        return None

    spacing_options = [joined]  # 붙임형은 항상 확신 있게 제시
    extra_notes = [note]

    # 띄어쓴 예시는 고신뢰일 때만(모든 조각 ≥2음절 + 전문분야 ≥1). 참고용임을 명시.
    if clean_cover and has_specialized:
        # 조각 자체가 띄어 쓰는 합성 표제어면 그 표기로 펼친다(나선은하→나선 은하).
        spaced = " ".join(spaced_map.get(p, p) for p in clean_cover)
        if spaced != joined:
            spacing_options.append(spaced)
            extra_notes.append(f"구성 예시(참고): {spaced} — 정확한 단어 경계는 사전 확인을 권장합니다.")
    else:
        extra_notes.append("정확한 단어 경계는 사전 확인을 권장합니다(분절은 신뢰도가 낮아 생략).")

    return InspectResult(
        input=text,
        found=True,
        rule_hints=[rule],
        spacing_options=list(dict.fromkeys(spacing_options)),
        notes=extra_notes,
    )
