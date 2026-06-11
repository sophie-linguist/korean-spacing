from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from build.build_index import build_index


def _write_sample_json(target: Path) -> None:
    payload = {
        "channel": {
            "item": [
                {
                    "wordinfo": {"word": "간섭성^빛", "word_unit": "구"},
                    "senseinfo": {
                        "pos": "명사",
                        "definition": "간섭성 빛",
                        "type": "일반어",
                        "cat_info": [{"cat": "물리"}],
                    },
                    "target_code": 1001,
                    "group_code": 10,
                    "group_order": 1,
                },
                {
                    "wordinfo": {"word": "차", "word_unit": "어휘"},
                    "senseinfo": {
                        "pos": "명사",
                        "definition": "수레를 이르는 말",
                        "type": "일반어",
                    },
                    "target_code": 1002,
                    "group_code": 11,
                    "group_order": 1,
                },
            ]
        }
    }
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_index_creates_rows_and_caret_fields(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _write_sample_json(src_dir / "sample.json")

    schema = Path("build/schema.sql")
    db = tmp_path / "dict.db"

    stats = build_index(src_dir, db, schema, batch_size=1)
    assert stats.files == 1
    assert stats.rows == 2

    con = sqlite3.connect(db)
    try:
        row = con.execute(
            "SELECT word_joined, word_spaced, has_caret, caret_count, type FROM entries WHERE target_code=1001"
        ).fetchone()
        assert row == ("간섭성빛", "간섭성 빛", 1, 1, "일반어")
    finally:
        con.close()


def test_build_index_idempotent_row_count(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _write_sample_json(src_dir / "sample.json")

    schema = Path("build/schema.sql")
    db = tmp_path / "dict.db"

    first = build_index(src_dir, db, schema, batch_size=2)
    second = build_index(src_dir, db, schema, batch_size=2)

    assert first.rows == second.rows == 2


def test_caret_entries_are_general_type_in_sample(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    _write_sample_json(src_dir / "sample.json")

    schema = Path("build/schema.sql")
    db = tmp_path / "dict.db"
    build_index(src_dir, db, schema, batch_size=1)

    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT type, COUNT(*) FROM entries WHERE has_caret=1 GROUP BY type"
        ).fetchall()
        assert rows == [("일반어", 1)]
    finally:
        con.close()
