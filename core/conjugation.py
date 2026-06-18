"""머리(용언 활용형) 검증 게이트 — 형태소분석기 없이 자모 연산 + 어미 표로 판정.

결합형 덩어리(예: '할만하다')를 '할' + '만하다'로 가를 때, 머리 '할'이 정말로
용언의 활용형인지 확인해 명사 오분할('주먹만하다'→'주먹 만하다')을 막는다.

원리: 머리에서 어미를 떼어 어간을 복원하고, '-다'를 붙인 기본형이 사전에 동사/형용사로
등록돼 있으면 통과. 한글 맞춤법 제15~18항(어간·어미, 불규칙 활용)과 제34~38항(준말/모음
축약)을 규칙으로 구현한다. 후보는 과생성해도 되며, 사전 조회로 실제 용언만 살아남는다
(self-filter). 모든 단계가 결정적 규칙(유니코드 자모 산술 + 유한 어미 표)이라 통계 모델이 없다.
"""

from __future__ import annotations

from core.local_index import exists_with_pos, get_connection, normalize_lookup_forms

_HANGUL_BASE = 0xAC00
_HANGUL_LAST = 0xD7A3
_JONG_COUNT = 28  # 종성 개수(없음 포함)

# 종성 인덱스(유니코드 종성 배열 기준)
_JONG_NONE = 0
_JONG_N = 4    # ㄴ
_JONG_D = 7    # ㄷ
_JONG_L = 8    # ㄹ
_JONG_B = 17   # ㅂ
_JONG_S = 19   # ㅅ
_JONG_H = 27   # ㅎ

# 초성 인덱스
_CHO_L = 5        # ㄹ
_CHO_IEUNG = 11   # ㅇ

# 중성 인덱스
_JUNG_A = 0       # ㅏ
_JUNG_AE = 1      # ㅐ
_JUNG_EO = 4      # ㅓ
_JUNG_E = 5       # ㅔ
_JUNG_YEO = 6     # ㅕ
_JUNG_O = 8       # ㅗ
_JUNG_WA = 9      # ㅘ
_JUNG_WAE = 10    # ㅙ
_JUNG_OE = 11     # ㅚ
_JUNG_U = 13      # ㅜ
_JUNG_WEO = 14    # ㅝ
_JUNG_EU = 18     # ㅡ
_JUNG_I = 20      # ㅣ

# 본용언계 보조용언 앞에 오는 보조적 연결어미(한 음절 형태).
_CONNECTIVE_SYLLABLES = ("아", "어", "여", "게", "지", "고", "서")

# 관형사형으로 쓰여 의존명사·보조형용사 앞에 오는 한 음절 어미.
_ADNOMINAL_SYLLABLES = ("을", "은", "는")

# 어간 복원이 불규칙이라 음절 분해로는 못 잡지만 매우 흔한 형태(여 불규칙 '하다').
_FUSED_HEADS = {
    "해": "하다",
    "하여": "하다",
}

_VERB_ADJ_POS_LIKE = "%동사%"  # '%형용사%'와 함께 OR로 검사
_ADJ_POS_LIKE = "%형용사%"


def is_hangul_syllable(ch: str) -> bool:
    return len(ch) == 1 and _HANGUL_BASE <= ord(ch) <= _HANGUL_LAST


def decompose(syllable: str) -> tuple[int, int, int]:
    """완성형 한글 음절을 (초성, 중성, 종성) 인덱스로 분해한다. 비한글이면 ValueError."""
    if not is_hangul_syllable(syllable):
        raise ValueError(f"not a hangul syllable: {syllable!r}")
    code = ord(syllable) - _HANGUL_BASE
    cho = code // (21 * _JONG_COUNT)
    jung = (code % (21 * _JONG_COUNT)) // _JONG_COUNT
    jong = code % _JONG_COUNT
    return cho, jung, jong


def compose(cho: int, jung: int, jong: int) -> str:
    """(초성, 중성, 종성) 인덱스를 완성형 한글 음절로 합성한다."""
    code = _HANGUL_BASE + (cho * 21 + jung) * _JONG_COUNT + jong
    return chr(code)


def _strip_coda(syllable: str) -> str:
    """음절의 종성을 떼어낸 음절을 돌려준다(받침 없는 음절)."""
    cho, jung, _ = decompose(syllable)
    return compose(cho, jung, _JONG_NONE)


# ── 어간 끝모음 + 아/어 축약 (제34~38항) ─────────────────────────────
# 어간 끝 모음 → '-아/-어'가 붙은 표면형 중성(축약 결과).
_EO_CONTRACTION = {
    _JUNG_A: _JUNG_A,      # 가+아 → 가
    _JUNG_EO: _JUNG_EO,    # 서+어 → 서
    _JUNG_AE: _JUNG_AE,    # 개+어 → 개
    _JUNG_E: _JUNG_E,      # 세+어 → 세
    _JUNG_O: _JUNG_WA,     # 보+아 → 봐
    _JUNG_U: _JUNG_WEO,    # 주+어 → 줘
    _JUNG_OE: _JUNG_WAE,   # 되+어 → 돼
    _JUNG_I: _JUNG_YEO,    # 보이+어 → 보여, 기다리+어 → 기다려
    _JUNG_EU: _JUNG_EO,    # 쓰+어 → 써 (으 탈락)
}

# 표면형 중성 → 어간 끝 모음 후보(역방향). 과생성 허용(사전 self-filter).
_EO_REVERSE = {
    _JUNG_YEO: (_JUNG_I,),         # 여 ← 이+어
    _JUNG_WA: (_JUNG_O,),          # 와/봐 ← 오+아
    _JUNG_WEO: (_JUNG_U,),         # 워/줘 ← 우+어
    _JUNG_WAE: (_JUNG_OE,),        # 왜/돼 ← 외+어
    _JUNG_EO: (_JUNG_EU, _JUNG_U), # 어/써 ← 으+어, 퍼 ← 푸(ㅜ 탈락)
    # 주의: 'ㅏ ← ㅡ'(따라←따르)는 명사 오인('나라'→'나르다')을 유발해 제외한다.
    # '르' 어간은 르불규칙(날라)과 ㅡ탈락(따라)이 같은 형태라 형태만으로 구별 불가하므로,
    # 명사 오분할 방지를 우선해 과생성을 막는다.
}

_PLAIN_CONNECTIVES = ("게", "지", "고")  # 축약 없이 어간에 바로 붙는 보조적 연결어미


def restore_stem_candidates(head: str) -> list[str]:
    """머리에서 어미를 떼어 가능한 기본형('어간'+'다') 후보들을 만든다.

    규칙활용 + 제18항 불규칙(ㄹ/ㅅ/ㄷ/ㅂ/ㅎ/르/러/ㅜ·ㅡ) + 제34~38항 준말 축약을
    역으로 복원한다. 과생성해도 되며 사전 조회로 실제 동사/형용사만 살아남는다.
    """
    stems: list[str] = []

    def add_stem(stem: str) -> None:
        if stem and stem not in stems:
            stems.append(stem)

    # 1) 한 음절 어미(을/은/는/게/지/고/아/어/여/서 …)를 통째로 떼기.
    for ending in (*_CONNECTIVE_SYLLABLES, *_ADNOMINAL_SYLLABLES):
        if len(ending) == 1 and is_hangul_syllable(ending):
            if len(head) > 1 and head.endswith(ending):
                add_stem(head[:-1])

    # 2) 마지막 음절의 종성이 어미인 경우(관형사형 -ㄹ/-ㄴ): 종성만 제거.
    last = head[-1]
    if is_hangul_syllable(last):
        _, _, jong = decompose(last)
        if jong in (_JONG_L, _JONG_N):
            add_stem(head[:-1] + _strip_coda(last))

    # 3) 규칙 어간에서 불규칙 원형 후보 파생(아는→알, 들을→듣, 도우→돕 …).
    for s in list(stems):
        for variant in _irregular_stem_variants(s):
            add_stem(variant)

    # 4) 어간이 곧 머리인 경우(가→가다, 자→자다). 단음절만 — 다음절 머리(다리·우리)는
    #    'head+다'로 명사-동사 동음(다리다·우리다)을 만들어 명사를 오인하므로 제외.
    if len(head) == 1:
        add_stem(head)

    # 5) 준말/모음 축약 역복원(봐→보, 보여→보이, 돼→되, 따라→따르 …).
    for stem in _reverse_contraction_stems(head):
        add_stem(stem)

    # 6) 제18항 불규칙 활용형 역복원(불러→부르, 도와→돕, 그래→그렇 …).
    for stem in _irregular_reverse(head):
        add_stem(stem)

    candidates = [s + "다" for s in stems]

    # 융합형(여 불규칙 '하다') 및 '…해 → …하다'.
    if head in _FUSED_HEADS:
        basic = _FUSED_HEADS[head]
        if basic not in candidates:
            candidates.insert(0, basic)
    if head.endswith("해") and len(head) > 1:
        ha = head[:-1] + "하다"
        if ha not in candidates:
            candidates.append(ha)

    # 중복 제거(순서 보존).
    seen: set[str] = set()
    unique: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    return unique


def _irregular_stem_variants(stem: str) -> list[str]:
    """규칙 어간 후보에서 불규칙 용언의 원형 어간을 파생한다(사전으로 self-filter)."""
    out: list[str] = []
    last = stem[-1]
    if not is_hangul_syllable(last):
        return out
    cho, jung, jong = decompose(last)

    if jong == _JONG_NONE:
        # ㄹ 불규칙(ㄹ 탈락 복원): 아는→알, 사는→살, 만드는→만들
        out.append(stem[:-1] + compose(cho, jung, _JONG_L))
        # ㅅ 불규칙: 지은→짓, 나아→낫
        out.append(stem[:-1] + compose(cho, jung, _JONG_S))
    if jong == _JONG_L:
        # ㄷ 불규칙: 들을→듣, 걸은→걷, 실은→싣
        out.append(stem[:-1] + compose(cho, jung, _JONG_D))
    # ㅂ 불규칙: 도우→돕, 고우→곱 (끝이 ㅇ+오/우, 받침 없음 → 앞 음절에 ㅂ받침)
    if cho == _CHO_IEUNG and jung in (_JUNG_O, _JUNG_U) and jong == _JONG_NONE and len(stem) >= 2:
        prev = stem[-2]
        if is_hangul_syllable(prev):
            pc, pj, pjong = decompose(prev)
            if pjong == _JONG_NONE:
                out.append(stem[:-2] + compose(pc, pj, _JONG_B))
    return out


def _reverse_contraction_stems(head: str) -> list[str]:
    """머리 끝 음절이 모음 축약형이면 어간 후보를 역으로 복원한다(보여→보이, 봐→보, 돼→되,
    꺼→끄, 따라→따르 …). 끝 음절의 중성만 후보 모음으로 치환한다."""
    out: list[str] = []
    last = head[-1]
    if not is_hangul_syllable(last):
        return out
    cho, jung, jong = decompose(last)
    if jong != _JONG_NONE:
        return out
    for underlying in _EO_REVERSE.get(jung, ()):
        out.append(head[:-1] + compose(cho, underlying, _JONG_NONE))
    return out


def _irregular_reverse(head: str) -> list[str]:
    """제18항 불규칙 활용형에서 기본 어간을 역복원한다(과생성, 사전 self-filter).

    - 르 불규칙: …Cㄹ + 라/러 → …C르 (불러→부르, 갈라→가르)
    - 러 불규칙: …르 + 러 → …르 (이르러→이르)
    - ㅂ 불규칙: …와/워 → … + ㅂ받침 (도와→돕, 구워→굽)
    - ㅎ 불규칙: …ㅐ → …{ㅏ,ㅓ} + ㅎ받침 (그래→그렇, 노래→노랗)
    """
    out: list[str] = []
    n = len(head)
    last = head[-1]
    if not is_hangul_syllable(last):
        return out
    lc, lj, ljong = decompose(last)

    # 르 불규칙: 앞 음절이 ㄹ받침이고 끝 음절이 ㄹ초성 + ㅏ/ㅓ → '…C르'
    if n >= 2 and lc == _CHO_L and lj in (_JUNG_A, _JUNG_EO) and ljong == _JONG_NONE:
        prev = head[-2]
        if is_hangul_syllable(prev):
            pc, pj, pjong = decompose(prev)
            if pjong == _JONG_L:
                out.append(head[:-2] + compose(pc, pj, _JONG_NONE) + "르")

    # 러 불규칙: '…르러' → '…르' (이르러→이르, 푸르러→푸르)
    if n >= 2 and last == "러" and head[-2] == "르":
        out.append(head[:-1])

    # ㅂ 불규칙: 끝 음절 ㅇ초성 + ㅘ/ㅝ → 끝 음절을 떼고 앞 음절에 ㅂ받침
    if lc == _CHO_IEUNG and lj in (_JUNG_WA, _JUNG_WEO) and ljong == _JONG_NONE and n >= 2:
        prev = head[-2]
        if is_hangul_syllable(prev):
            pc, pj, pjong = decompose(prev)
            if pjong == _JONG_NONE:
                out.append(head[:-2] + compose(pc, pj, _JONG_B))

    # ㅎ 불규칙: 끝 음절 ㅐ(받침 없음) → {ㅏ,ㅓ} + ㅎ받침
    if lj == _JUNG_AE and ljong == _JONG_NONE:
        for v in (_JUNG_A, _JUNG_EO):
            out.append(head[:-1] + compose(lc, v, _JONG_H))

    return out


def _is_registered_predicate(basic_form: str) -> bool:
    """기본형이 사전에 동사 또는 형용사로 등록돼 있는지."""
    return exists_with_pos(basic_form, _VERB_ADJ_POS_LIKE) or exists_with_pos(
        basic_form, _ADJ_POS_LIKE
    )


def _is_general_predicate(basic_form: str) -> bool:
    """기본형이 '일반어' 동사/형용사로 등재돼 있는지(방언/북한어/옛말 제외)."""
    joined, _ = normalize_lookup_forms(basic_form)
    con = get_connection()
    row = con.execute(
        "SELECT 1 FROM entries WHERE word_joined = ? AND type = '일반어' "
        "AND (pos LIKE '%동사%' OR pos LIKE '%형용사%') LIMIT 1",
        (joined,),
    ).fetchone()
    return row is not None


def is_predicate_inflection(head: str, db_path: str | None = None) -> bool:
    """머리가 용언 활용형으로 볼 수 있는지 판정한다(게이트).

    어미를 떼어 복원한 기본형 후보 중 하나라도 사전의 동사/형용사면 True.
    하나도 없으면 False → 호출부는 분리를 포기하고 침묵한다.
    """
    head = head.strip()
    if not head:
        return False

    for basic_form in restore_stem_candidates(head):
        if _is_registered_predicate(basic_form):
            return True
    return False


# ── 본용언 기본형 복원 + 정확도(역방향 활용 검증) ──────────────────
def _attach_eo(stem: str) -> str | None:
    """어간에 보조적 연결어미 -아/-어를 붙인 표면형을 만든다(모음 축약 반영)."""
    if not stem or not is_hangul_syllable(stem[-1]):
        return None
    cho, jung, jong = decompose(stem[-1])
    if jong != _JONG_NONE:
        eo = "아" if jung in (_JUNG_A, _JUNG_O) else "어"
        return stem + eo
    if jung in _EO_CONTRACTION:
        return stem[:-1] + compose(cho, _EO_CONTRACTION[jung], _JONG_NONE)
    eo = "아" if jung in (_JUNG_A, _JUNG_O) else "어"
    return stem + eo


def _eo_surface_forms(stem: str) -> set[str]:
    """어간을 '-아/-어'로 활용한 표면형 후보 집합(규칙 + 제18항 불규칙 정방향)."""
    forms: set[str] = set()
    if not stem or not is_hangul_syllable(stem[-1]):
        return forms
    cho, jung, jong = decompose(stem[-1])

    # 규칙(비축약 + 축약)
    forms.add(stem + "아")
    forms.add(stem + "어")
    ae = _attach_eo(stem)
    if ae:
        forms.add(ae)

    # 하다(여 불규칙): 하여 / 해
    if stem.endswith("하"):
        forms.add(stem + "여")
        forms.add(stem[:-1] + "해")

    # 르 불규칙: …르 → 앞 음절 ㄹ받침 + 라/러 (부르→불러, 가르→갈라)
    if jung == _JUNG_EU and cho == _CHO_L and len(stem) >= 2:
        prev = stem[-2]
        if is_hangul_syllable(prev):
            pc, pj, pjong = decompose(prev)
            if pjong == _JONG_NONE:
                ra = "라" if pj in (_JUNG_A, _JUNG_O) else "러"
                forms.add(stem[:-2] + compose(pc, pj, _JONG_L) + ra)
        # 러 불규칙: …르 → …르러 (이르→이르러, 푸르→푸르러)
        forms.add(stem + "러")

    # ㅅ 불규칙: ㅅ받침 → 받침 제거 + 아/어 (짓→지어, 낫→나아)
    if jong == _JONG_S:
        base = compose(cho, jung, _JONG_NONE)
        eo = "아" if jung in (_JUNG_A, _JUNG_O) else "어"
        forms.add(stem[:-1] + base + eo)

    # ㄷ 불규칙: ㄷ받침 → ㄹ받침 + 아/어 (걷→걸어, 듣→들어)
    if jong == _JONG_D:
        eo = "아" if jung in (_JUNG_A, _JUNG_O) else "어"
        forms.add(stem[:-1] + compose(cho, jung, _JONG_L) + eo)

    # ㅂ 불규칙: ㅂ받침 → 받침 제거 + 와/워
    if jong == _JONG_B:
        base = compose(cho, jung, _JONG_NONE)
        wa = "와" if jung in (_JUNG_A, _JUNG_O) else "워"
        forms.add(stem[:-1] + base + wa)

    # ㅎ 불규칙: ㅎ받침 → 받침 제거 + 중성 ㅐ
    if jong == _JONG_H:
        forms.add(stem[:-1] + compose(cho, _JUNG_AE, _JONG_NONE))

    # ㅜ 탈락: 끝 음절 ㅜ(받침 없음) → ㅓ (푸→퍼)
    if jung == _JUNG_U and jong == _JONG_NONE:
        forms.add(stem[:-1] + compose(cho, _JUNG_EO, _JONG_NONE))

    # ㅡ 탈락: 끝 음절 ㅡ(받침 없음) → 앞 음절 모음조화로 ㅏ/ㅓ (끄→꺼, 따르→따라)
    if jung == _JUNG_EU and jong == _JONG_NONE:
        if len(stem) >= 2 and is_hangul_syllable(stem[-2]):
            _, pj, _ = decompose(stem[-2])
            v = _JUNG_A if pj in (_JUNG_A, _JUNG_O) else _JUNG_EO
        else:
            v = _JUNG_EO
        forms.add(stem[:-1] + compose(cho, v, _JONG_NONE))

    return forms


def _adnominal_forms(stem: str) -> set[str]:
    """어간의 관형사형 표면형 집합(-(으)ㄴ/-는/-(으)ㄹ, 불규칙 포함). 알→{아는,안,알}."""
    forms: set[str] = set()
    if not stem or not is_hangul_syllable(stem[-1]):
        return forms
    c, j, jo = decompose(stem[-1])

    if jo == _JONG_NONE:
        # 모음 어간: +ㄴ, +ㄹ, +는 (간/갈/가는, 한/할/하는)
        forms.add(stem[:-1] + compose(c, j, _JONG_N))
        forms.add(stem[:-1] + compose(c, j, _JONG_L))
        forms.add(stem + "는")
        return forms

    # 자음 어간: +은, +을, +는
    forms.add(stem + "은")
    forms.add(stem + "을")
    forms.add(stem + "는")
    if jo == _JONG_L:  # ㄹ 어간: 알→아는, 안, 알
        base = stem[:-1] + compose(c, j, _JONG_NONE)
        forms.add(base + "는")
        forms.add(stem[:-1] + compose(c, j, _JONG_N))
        forms.add(stem)
    if jo == _JONG_D:  # ㄷ 불규칙: 걷→걸은/걸을
        ll = stem[:-1] + compose(c, j, _JONG_L)
        forms.add(ll + "은")
        forms.add(ll + "을")
    if jo == _JONG_B:  # ㅂ 불규칙: 돕→도운/도울
        base = stem[:-1] + compose(c, j, _JONG_NONE)
        forms.add(base + "운")
        forms.add(base + "울")
    if jo == _JONG_S:  # ㅅ 불규칙: 짓→지은/지을
        base = stem[:-1] + compose(c, j, _JONG_NONE)
        forms.add(base + "은")
        forms.add(base + "을")
    return forms


def head_matches_base(head: str, base_form: str) -> bool:
    """기본형(어간+다)을 다시 활용했을 때 입력 머리(head)가 재현되는지 검증한다.

    -아/-어(축약·불규칙 포함), -게/-지/-고, 관형사형(-(으)ㄴ/-는/-(으)ㄹ)을 확인한다.
    하나라도 머리와 일치하면 True → '정확도 높음'. 표준형은 통과하고 비표준 동음
    (불르다·그래다)이나 잘못 복원된 어간(아는→앗다)은 떨어진다.
    """
    if not base_form.endswith("다"):
        return False
    stem = base_form[:-1]
    if not stem:
        return False

    if head in _eo_surface_forms(stem):
        return True
    if head in _adnominal_forms(stem):
        return True
    for c in _PLAIN_CONNECTIVES:
        if head == stem + c:
            return True
    return False


def base_forms_with_confidence(
    head: str, db_path: str | None = None
) -> list[tuple[str, bool]]:
    """머리에서 복원 가능한 본용언 기본형 후보를 (기본형, 정확도높음) 목록으로 돌려준다.

    사전에 동사/형용사로 등재된 후보만 남기고, 역방향 활용 검증을 통과하면
    정확도 높음(True), 등재는 됐지만 재현이 안 되면 False(참고)로 표시한다.
    정확도 높음 후보가 있으면 그것만, 없으면 후보 전체를 '참고'로 노출한다.
    """
    head = head.strip()

    high: list[tuple[str, bool]] = []
    low: list[tuple[str, bool]] = []
    seen: set[str] = set()
    for base in restore_stem_candidates(head):
        if base in seen:
            continue
        seen.add(base)
        if not _is_registered_predicate(base):
            continue
        if head_matches_base(head, base):
            high.append((base, True))
        else:
            low.append((base, False))

    # 표준어(일반어) 동사/형용사 후보가 있으면 방언 동음(불르다·몰라다 등)은 제외.
    general_high = [pair for pair in high if _is_general_predicate(pair[0])]
    if general_high:
        high = general_high

    high.sort(key=lambda x: len(x[0]))
    low.sort(key=lambda x: len(x[0]))
    return high if high else low
