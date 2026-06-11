from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core import inspect

EXAMPLES = ["아는데", "법대로", "회의중", "할만하다", "차한대", "인공지능위원회"]
MAX_INPUT_LEN = 20

FONT_MAIN = ("Malgun Gothic", 10)
FONT_HEAD = ("Malgun Gothic", 11, "bold")
FONT_BIG = ("Malgun Gothic", 15, "bold")
FONT_LABEL = ("Malgun Gothic", 9, "bold")
FONT_MUTED = ("Malgun Gothic", 9)

COLOR_SPACE = "#1a7f37"   # 띄어 씀(초록)
COLOR_JOIN = "#0969da"    # 붙여 씀(파랑)
COLOR_RULE = "#8250df"    # 조항(보라)
COLOR_MUTED = "#57606a"
COLOR_HEAD = "#111111"


def _is_spaced(option: str) -> bool:
    return " " in option.strip()


class SpacingApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("한국어 띄어쓰기 조회 도구")
        self.root.geometry("1000x720")

        self.query_var = tk.StringVar()
        self.status_var = tk.StringVar(value="단어 또는 짧은 표현을 입력하세요. 예) 아는데 · 법대로 · 회의중")

        self._build_layout()

    def _build_layout(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="입력", font=FONT_HEAD).pack(side=tk.LEFT)
        entry = ttk.Entry(top, textvariable=self.query_var, font=FONT_BIG, width=28)
        entry.pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", lambda _e: self.run_query())
        entry.focus_set()
        ttk.Button(top, text="조회", command=self.run_query).pack(side=tk.LEFT)

        chips = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        chips.pack(fill=tk.X)
        ttk.Label(chips, text="예시:", font=FONT_MUTED).pack(side=tk.LEFT)
        for ex in EXAMPLES:
            ttk.Button(chips, text=ex, width=12, command=lambda q=ex: self.run_query(q)).pack(side=tk.LEFT, padx=3)

        ttk.Label(self.root, textvariable=self.status_var, foreground=COLOR_MUTED, font=FONT_MUTED).pack(
            fill=tk.X, padx=12, pady=(0, 6)
        )

        body = ttk.Frame(self.root, padding=12)
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(0, weight=1)

        # 왼쪽: 띄어쓰기 판단(주역)
        left = ttk.LabelFrame(body, text=" 띄어쓰기 판단 ", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.answer_text = tk.Text(left, wrap=tk.WORD, font=FONT_MAIN, bg="#ffffff", relief=tk.FLAT, padx=6, pady=6)
        self.answer_text.pack(fill=tk.BOTH, expand=True)

        # 오른쪽: 사전 근거
        right = ttk.LabelFrame(body, text=" 사전 근거 ", padding=10)
        right.grid(row=0, column=1, sticky="nsew")
        self.dict_text = tk.Text(right, wrap=tk.WORD, font=FONT_MAIN, bg="#f6f8fa", relief=tk.FLAT, padx=6, pady=6)
        self.dict_text.pack(fill=tk.BOTH, expand=True)

        for widget in (self.answer_text, self.dict_text):
            self._configure_tags(widget)

    def _configure_tags(self, t: tk.Text) -> None:
        t.tag_configure("head", font=FONT_HEAD, foreground=COLOR_HEAD, spacing1=8, spacing3=4)
        t.tag_configure("big_space", font=FONT_BIG, foreground=COLOR_SPACE, spacing3=2)
        t.tag_configure("big_join", font=FONT_BIG, foreground=COLOR_JOIN, spacing3=2)
        t.tag_configure("label_space", font=FONT_LABEL, foreground=COLOR_SPACE)
        t.tag_configure("label_join", font=FONT_LABEL, foreground=COLOR_JOIN)
        t.tag_configure("rule", font=FONT_LABEL, foreground=COLOR_RULE)
        t.tag_configure("body", font=FONT_MAIN, foreground="#1f2328", lmargin1=14, lmargin2=14, spacing3=6)
        t.tag_configure("muted", font=FONT_MUTED, foreground=COLOR_MUTED, lmargin1=8, lmargin2=8, spacing3=3)
        t.tag_configure("scissor", font=FONT_HEAD, foreground="#bc4c00", spacing1=8)

    def run_query(self, preset: str | None = None) -> None:
        query = (preset if preset is not None else self.query_var.get()).strip()
        self.query_var.set(query)

        if not query:
            self.status_var.set("검색어를 입력하세요.")
            return
        if len(query) > MAX_INPUT_LEN:
            self.status_var.set(f"입력 길이는 {MAX_INPUT_LEN}자 이하여야 합니다.")
            return

        try:
            result = inspect(query)
        except FileNotFoundError:
            self.status_var.set("사전 파일(dict.db)을 찾을 수 없습니다 — exe와 같은 폴더에 두세요.")
            return
        except Exception:
            self.status_var.set("인덱스가 손상되었을 수 있습니다 — 다시 빌드하세요.")
            return

        self._render(result)

    def _render(self, result) -> None:
        a, d = self.answer_text, self.dict_text
        for t in (a, d):
            t.config(state=tk.NORMAL)
            t.delete("1.0", tk.END)

        if not result.found:
            self.status_var.set(f"‘{result.input}’ — 딱 맞는 결과가 없어요.")
            a.insert(tk.END, "딱 맞는 결과가 없어요\n", "head")
            a.insert(tk.END, f"‘{result.input}’ — 사전에 없고, 규칙으로도 분명히 가르기 어려웠어요.\n", "muted")
            a.insert(tk.END, "이렇게 다시 검색해 보세요\n", "head")
            for tip in (
                "동사·형용사는 기본형으로 — ‘먹었어요’ → ‘먹다’",
                "띄어쓰기가 궁금하면 붙여서 — ‘아는데’, ‘차한대’, ‘회의중’",
                "긴 문장보다 짧은 표현 하나로",
            ):
                a.insert(tk.END, "• " + tip + "\n", "muted")
            for t in (a, d):
                t.config(state=tk.DISABLED)
            return

        self.status_var.set(f"‘{result.input}’ 조회 완료")

        # ── 왼쪽: 표기 옵션(답) ──
        if result.spacing_options:
            a.insert(tk.END, "이렇게 쓸 수 있어요\n", "head")
            for opt in result.spacing_options:
                spaced = _is_spaced(opt)
                a.insert(tk.END, "  띄어 씀  " if spaced else "  붙여 씀  ",
                         "label_space" if spaced else "label_join")
                a.insert(tk.END, opt + "\n", "big_space" if spaced else "big_join")
            a.insert(tk.END, "\n")

        # ── 왼쪽: 조항 근거(해석 카드) ──
        if result.rule_hints:
            a.insert(tk.END, "조항 근거\n", "head")
            for h in result.rule_hints:
                a.insert(tk.END, f"  {h.항번호}  ", "rule")
                a.insert(tk.END, f"[{h.원칙허용}]\n", "label_space" if "띄" in h.원칙허용 else "label_join")
                a.insert(tk.END, h.요지 + "\n", "body")

        # ── 왼쪽: 분리 안내 ──
        if result.segmentation and result.segmentation.candidates:
            a.insert(tk.END, f"✂ {result.segmentation.message}\n", "scissor")
            for c in result.segmentation.candidates:
                a.insert(tk.END, f"  {c.original} → {c.left} + {c.right}\n", "body")

        # ── 왼쪽: 도움말 ──
        if result.notes:
            a.insert(tk.END, "도움말\n", "head")
            for note in result.notes:
                a.insert(tk.END, "• " + note + "\n", "muted")

        # ── 오른쪽: 사전 뜻풀이 ──
        if result.entries:
            d.insert(tk.END, "사전 뜻풀이\n", "head")
            for e in result.entries:
                badge = f"  · {e.spacing_badge}" if e.spacing_badge else ""
                d.insert(tk.END, f"• {e.word}  [{e.pos}]{badge}\n", "body")
                if e.definition:
                    d.insert(tk.END, f"   {e.definition}\n", "muted")
        else:
            d.insert(tk.END, "사전 표제어 없음 — 규정으로 판단합니다.\n", "muted")

        for t in (a, d):
            t.config(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    SpacingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
