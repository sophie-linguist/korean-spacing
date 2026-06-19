"""MCP(stdio) 셸 — core.inspect()를 도구로 노출한다.

다른 셸(webui·gui)과 같은 원칙: 언어 로직은 전부 core에 있고, 여기서는 입력을 받아
core.inspect()를 호출하고 결과를 직렬화해 돌려줄 뿐이다(얇은 셸).

실행:
    KOREAN_SPACING_DB_PATH=/경로/dict.db  python -m shell.mcp.server

연결(예: Claude Desktop / Claude Code의 mcpServers 설정):
    {
      "korean-spacing": {
        "command": "python",
        "args": ["-m", "shell.mcp.server"],
        "env": {"KOREAN_SPACING_DB_PATH": "/경로/dict.db"}
      }
    }
"""

from __future__ import annotations

import re

from mcp.server.fastmcp import FastMCP

from core import inspect as core_inspect
from core.local_index import lookup
from core.pos_mapper import load_rules
from core.serialize import result_to_text

# 단어·짧은 표현 단위 도구이므로 입력 길이를 제한한다(긴 문장은 대상이 아님).
MAX_INPUT_LEN = 20

mcp = FastMCP("korean-spacing")


@mcp.tool()
def inspect_spacing(text: str) -> str:
    """붙여 쓴 한국어 표현의 띄어쓰기를 우리말샘 사전과 한글 맞춤법으로 판정해 *근거와 함께* 설명한다.

    교정기가 아니라 '설명기'다. 사전 품사·해당 조항(제2·41~50항)을 들어 왜 그렇게 띄거나
    붙이는지 보여 준다. 답이 맥락으로만 갈리면(예: '본대로') 두 해석을 함께 제시하고,
    확신이 없으면 단정하지 않고 다시 검색하라고 안내한다.

    입력은 단어나 짧은 표현 하나(붙여 쓴 형태)로 넣는다.
    예: '얼마만큼', '할만하다', '아는데', '정상나선은하', '삼천이백억오천만원', '차한대'.
    문장 전체나 여러 어절은 대상이 아니다.
    """
    text = (text or "").strip()
    if not text:
        return "입력이 비어 있습니다. 띄어쓰기가 궁금한 표현을 붙여 써서 넣어 주세요."
    if len(text) > MAX_INPUT_LEN:
        return f"입력이 너무 깁니다(최대 {MAX_INPUT_LEN}자). 단어나 짧은 표현 단위로 검색해 주세요."

    try:
        result = core_inspect(text)
    except FileNotFoundError:
        return (
            "사전(dict.db)을 찾을 수 없습니다. 환경변수 KOREAN_SPACING_DB_PATH로 "
            "dict.db 경로를 지정해 주세요."
        )

    return result_to_text(result)


@mcp.tool()
def search_dictionary(word: str) -> str:
    """우리말샘 사전에서 표제어를 찾아 품사와 뜻풀이를 돌려준다.

    띄어쓰기 판정이 아니라 '이 단어가 사전에 있나, 품사·뜻이 무엇인가'를 확인할 때 쓴다.
    붙여 쓴 형과 띄어 쓴 형 모두로 조회한다(예: '나선은하' 또는 '나선 은하').
    """
    word = (word or "").strip()
    if not word:
        return "검색어가 비어 있습니다."
    try:
        rows = lookup(word)
    except FileNotFoundError:
        return "사전(dict.db)을 찾을 수 없습니다. KOREAN_SPACING_DB_PATH를 확인해 주세요."

    if not rows:
        return f"‘{word}’: 우리말샘에 등재된 표제어를 찾지 못했습니다."

    lines = [f"‘{word}’ 우리말샘 검색 결과 {len(rows)}건:"]
    for r in rows[:20]:
        disp = (r.get("word_raw") or "").replace("^", " ").replace("-", "")
        pos = r.get("pos") or "-"
        typ = r.get("type") or ""
        defi = (r.get("definition") or "").strip()
        typ_s = f" · {typ}" if typ and typ != "일반어" else ""
        lines.append(f"- {disp} ({pos}{typ_s}): {defi}")
    if len(rows) > 20:
        lines.append(f"… 외 {len(rows) - 20}건")
    return "\n".join(lines)


@mcp.tool()
def get_rule(clause: str) -> str:
    """한글 맞춤법 띄어쓰기 조항의 원문·예시·해설을 돌려준다.

    clause는 항 번호다. '제42항', '42' 등 숫자가 들어간 형태면 모두 인식한다.
    지원 범위: 제2항(기본 원칙)과 제5장 제41~50항.
    """
    m = re.search(r"\d+", clause or "")
    if not m:
        return "조항 번호를 찾을 수 없습니다. 예: '제42항' 또는 '42'."

    key = f"제{m.group()}항"
    c = load_rules().get(key)
    if c is None:
        return f"{key}: 해당 조항을 찾지 못했습니다(제2항·제41~50항을 지원합니다)."

    lines = [f"{key} — {c.get('조항', '')}"]
    exs = c.get("예시") or []
    if exs:
        lines.append("예시: " + ", ".join(str(e) for e in exs))
    note = c.get("해설") or ""
    if note:
        lines.append("해설: " + note)
    return "\n".join(lines)


def main() -> None:
    mcp.run()  # 기본 transport=stdio


if __name__ == "__main__":
    main()
