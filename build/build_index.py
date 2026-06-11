from __future__ import annotations

import argparse
import json
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ijson


@dataclass(slots=True)
class BuildStats:
    files: int = 0
    rows: int = 0


def normalize_nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def normalize_word_forms(word: str) -> tuple[str, str, str, int, int]:
    raw = normalize_nfc((word or "").strip())
    caret_count = raw.count("^")
    has_caret = 1 if caret_count > 0 else 0

    joined = raw.replace("^", "").replace("-", "").replace(" ", "")
    joined = normalize_nfc(joined)

    spaced_source = raw.replace("^", " ").replace("-", " ")
    spaced = normalize_nfc(" ".join(spaced_source.split()))

    return raw, joined, spaced, has_caret, caret_count


def extract_cat(senseinfo: dict[str, Any]) -> str | None:
    cat_info = senseinfo.get("cat_info")
    if not isinstance(cat_info, list):
        return None

    cats: list[str] = []
    for item in cat_info:
        if not isinstance(item, dict):
            continue
        cat = item.get("cat")
        if isinstance(cat, str) and cat.strip():
            cats.append(normalize_nfc(cat.strip()))

    if not cats:
        return None
    return "|".join(cats)


def iter_items(json_path: Path):
    with json_path.open("rb") as fh:
        for item in ijson.items(fh, "channel.item.item"):
            if isinstance(item, dict):
                yield item


def create_db(db_path: Path, schema_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")

    schema_sql = schema_path.read_text(encoding="utf-8")
    con.executescript(schema_sql)
    return con


def insert_item(con: sqlite3.Connection, item: dict[str, Any]) -> None:
    wordinfo = item.get("wordinfo") or {}
    senseinfo = item.get("senseinfo") or {}

    word = wordinfo.get("word")
    if not isinstance(word, str) or not word.strip():
        return

    raw, joined, spaced, has_caret, caret_count = normalize_word_forms(word)

    definition = senseinfo.get("definition") or senseinfo.get("definition_original") or ""
    if not isinstance(definition, str):
        definition = str(definition)

    pos = senseinfo.get("pos")
    if not isinstance(pos, str):
        pos = ""

    word_unit = wordinfo.get("word_unit")
    if not isinstance(word_unit, str):
        word_unit = ""

    type_ = senseinfo.get("type")
    if not isinstance(type_, str):
        type_ = ""

    target_code = item.get("target_code")
    if isinstance(target_code, str) and target_code.isdigit():
        target_code = int(target_code)
    if not isinstance(target_code, int):
        return

    group_code = item.get("group_code")
    if isinstance(group_code, str) and group_code.isdigit():
        group_code = int(group_code)
    if not isinstance(group_code, int):
        group_code = None

    group_order = item.get("group_order")
    if isinstance(group_order, str) and group_order.isdigit():
        group_order = int(group_order)
    if not isinstance(group_order, int):
        group_order = None

    con.execute(
        """
        INSERT OR REPLACE INTO entries (
            target_code,
            word_raw,
            word_joined,
            word_spaced,
            word_unit,
            pos,
            definition,
            type,
            cat,
            group_code,
            group_order,
            has_caret,
            caret_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            target_code,
            raw,
            joined,
            spaced,
            normalize_nfc(word_unit),
            normalize_nfc(pos),
            normalize_nfc(definition),
            normalize_nfc(type_),
            extract_cat(senseinfo),
            group_code,
            group_order,
            has_caret,
            caret_count,
        ),
    )


def build_index(source_dir: Path, db_path: Path, schema_path: Path, batch_size: int = 5000) -> BuildStats:
    json_files = sorted(source_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found under: {source_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    stats = BuildStats(files=len(json_files), rows=0)

    con = create_db(db_path, schema_path)
    try:
        pending = 0
        for json_file in json_files:
            for item in iter_items(json_file):
                insert_item(con, item)
                pending += 1
                stats.rows += 1
                if pending >= batch_size:
                    con.commit()
                    pending = 0
            con.commit()
        con.commit()
    finally:
        con.close()

    return stats


def _is_hangul_only(text: str) -> bool:
    return bool(text) and all(0xAC00 <= ord(ch) <= 0xD7A3 for ch in text)


def extract_tail_lexicon(db_path: Path, output_json: Path) -> dict[str, int]:
    """dict.db에서 결합형 분리에 쓰는 '꼬리' 집합을 뽑아 JSON으로 저장한다.

    보조 용언(pos LIKE '보조%')과 의존 명사(pos LIKE '%의존 명사%')의 word_joined
    고유값을 모은다. 손으로 적은 목록을 대체하므로 사전 갱신 시 자동 반영된다.
    한 단어가 양쪽에 걸치면 보조 용언(동사성)을 우선한다.
    """
    con = sqlite3.connect(str(db_path))
    try:
        aux = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT word_joined FROM entries WHERE pos LIKE '보조%'"
            )
            if _is_hangul_only(r[0])
        }
        dep = {
            r[0]
            for r in con.execute(
                "SELECT DISTINCT word_joined FROM entries WHERE pos LIKE '%의존 명사%'"
            )
            if _is_hangul_only(r[0])
        }
    finally:
        con.close()

    dep -= aux  # 겹치면 보조 용언 우선
    payload = {
        "aux_verb": sorted(aux),
        "dep_noun": sorted(dep),
    }
    output_json.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {"aux_verb": len(aux), "dep_noun": len(dep)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SQLite index from 우리말샘 JSON dump")
    parser.add_argument("--source", required=True, help="Directory containing JSON dump files")
    parser.add_argument("--output", required=True, help="Output SQLite database path")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).with_name("schema.sql")),
        help="SQLite schema file path",
    )
    parser.add_argument("--batch-size", type=int, default=5000, help="Commit batch size")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    source_dir = Path(args.source)
    db_path = Path(args.output)
    schema_path = Path(args.schema)

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_dir}")
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file does not exist: {schema_path}")

    stats = build_index(source_dir, db_path, schema_path, batch_size=args.batch_size)
    print(f"build-complete files={stats.files} rows={stats.rows} output={db_path}")

    lexicon_path = Path(__file__).resolve().parent.parent / "core" / "aux_lexicon.json"
    counts = extract_tail_lexicon(db_path, lexicon_path)
    print(
        f"lexicon-complete aux_verb={counts['aux_verb']} dep_noun={counts['dep_noun']} "
        f"output={lexicon_path}"
    )


if __name__ == "__main__":
    main()
