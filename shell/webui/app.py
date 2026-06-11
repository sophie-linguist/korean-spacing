"""웹(HTML/CSS) UI 셸 — pywebview로 네이티브 창 안에 웹페이지처럼 렌더링한다.

core.inspect() 로직은 그대로 두고, 결과를 JSON으로 직렬화해 JS에 넘긴다.
JS는 window.pywebview.api.inspect(query)로 호출한다.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import webview

from core import inspect as core_inspect
from core.pos_mapper import load_rules

WINDOW_TITLE = "한국어 띄어쓰기는 어려워"
MAX_INPUT_LEN = 20


def _clause_details(label: str) -> list[dict]:
    """'제42·45항' 같은 라벨에서 각 항의 전문·예시·해설을 모은다."""
    rules = load_rules()
    details: list[dict] = []
    for num in re.findall(r"\d+", label):
        clause = rules.get(f"제{num}항")
        if clause is None:
            continue
        details.append(
            {
                "num": f"제{num}항",
                "text": clause.get("조항", ""),
                "examples": clause.get("예시", []) or [],
                "commentary": clause.get("해설", ""),
            }
        )
    return details


def _result_to_dict(r) -> dict:
    """InspectResult(중첩 dataclass)를 JS 친화적 ascii 키 dict로 변환."""
    return {
        "input": r.input,
        "found": r.found,
        "hint": r.hint,
        "spacing_options": list(r.spacing_options),
        "rule_hints": [
            {
                "clause": h.항번호,
                "policy": h.원칙허용,
                "gist": h.요지,
                "details": _clause_details(h.항번호),
            }
            for h in r.rule_hints
        ],
        "entries": [
            {
                "word": e.word,
                "pos": e.pos,
                "definition": e.definition,
                "type": e.type,
                "badge": e.spacing_badge,
            }
            for e in r.entries
        ],
        "segmentation": (
            None
            if not r.segmentation
            else {
                "message": r.segmentation.message,
                "candidates": [
                    {"original": c.original, "left": c.left, "right": c.right, "hint": c.hint}
                    for c in r.segmentation.candidates
                ],
            }
        ),
        "notes": list(r.notes),
    }


class Api:
    """JS에서 호출하는 백엔드 브리지."""

    def inspect(self, query: str) -> dict:
        query = (query or "").strip()
        if not query:
            return {"error": "empty"}
        if len(query) > MAX_INPUT_LEN:
            return {"error": "too_long", "max": MAX_INPUT_LEN}
        try:
            result = core_inspect(query)
        except FileNotFoundError:
            return {"error": "dict_not_found"}
        except Exception:
            return {"error": "index_error"}
        return _result_to_dict(result)

    def get_rules_summary(self) -> list[dict]:
        """사이드바용 규정 유형별 요약을 돌려준다."""
        rules = load_rules()
        categories = [
            {"id": "c2", "title": "기본 원칙", "clauses": ["제2항"],
             "summary": "문장의 각 단어는 띄어 씀을 원칙으로 한다."},
            {"id": "c41", "title": "조사", "clauses": ["제41항"],
             "summary": "조사는 앞말에 붙여 쓴다. (꽃이, 학교에서처럼)"},
            {"id": "c42", "title": "의존 명사", "clauses": ["제42항"],
             "summary": "의존 명사는 띄어 쓴다. (아는 것, 할 수, 먹을 만큼)"},
            {"id": "c43", "title": "단위 명사", "clauses": ["제43항"],
             "summary": "단위 명사는 띄어 쓴다. 숫자 뒤 붙여 쓸 수 있다. (차 한 대)"},
            {"id": "c44", "title": "수의 띄어쓰기", "clauses": ["제44항"],
             "summary": "수를 적을 때 만 단위로 띄어 쓴다."},
            {"id": "c45", "title": "열거하는 말", "clauses": ["제45항"],
             "summary": "겸, 및, 등, 대 등 열거하는 말은 띄어 쓴다."},
            {"id": "c46", "title": "단음절 연속", "clauses": ["제46항"],
             "summary": "단음절 단어가 연이어 나타날 때 붙여 쓸 수 있다."},
            {"id": "c47", "title": "보조 용언", "clauses": ["제47항"],
             "summary": "보조 용언은 띄어 씀이 원칙, 붙여 씀도 허용. (먹어 보다/먹어보다)"},
            {"id": "c48", "title": "이름과 호칭", "clauses": ["제48항"],
             "summary": "성과 이름은 붙여 쓰고 호칭어는 띄어 쓴다. (홍길동 씨)"},
            {"id": "c49", "title": "고유 명사", "clauses": ["제49항"],
             "summary": "고유 명사는 단어별로 띄어 씀이 원칙, 단위별 붙여 쓸 수 있다."},
            {"id": "c50", "title": "전문 용어", "clauses": ["제50항"],
             "summary": "전문 용어는 띄어 씀이 원칙, 붙여 쓸 수 있다."},
        ]
        result = []
        for cat in categories:
            details = []
            for clause_id in cat["clauses"]:
                clause = rules.get(clause_id)
                if clause:
                    details.append({
                        "num": clause_id,
                        "text": clause.get("조항", ""),
                        "examples": clause.get("예시", []) or [],
                        "commentary": clause.get("해설", ""),
                    })
            result.append({
                "id": cat["id"],
                "title": cat["title"],
                "summary": cat["summary"],
                "details": details,
            })
        return result


def _html_path() -> Path:
    # PyInstaller onefile에서도 동작하도록 _MEIPASS 우선.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidate = base / "shell" / "webui" / "index.html"
    if candidate.exists():
        return candidate
    return Path(__file__).resolve().parent / "index.html"


def main() -> None:
    html = _html_path().read_text(encoding="utf-8")
    webview.create_window(
        WINDOW_TITLE,
        html=html,
        js_api=Api(),
        width=1040,
        height=780,
        min_size=(840, 620),
        background_color="#0f1115",
    )
    webview.start()


if __name__ == "__main__":
    main()
