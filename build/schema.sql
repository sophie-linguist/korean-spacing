PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS entries (
    target_code INTEGER PRIMARY KEY,
    word_raw TEXT NOT NULL,
    word_joined TEXT NOT NULL,
    word_spaced TEXT NOT NULL,
    word_unit TEXT,
    pos TEXT,
    definition TEXT,
    type TEXT,
    cat TEXT,
    group_code INTEGER,
    group_order INTEGER,
    has_caret INTEGER NOT NULL DEFAULT 0 CHECK (has_caret IN (0, 1)),
    caret_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_entries_word_joined ON entries(word_joined);
CREATE INDEX IF NOT EXISTS idx_entries_word_spaced ON entries(word_spaced);
CREATE INDEX IF NOT EXISTS idx_entries_group_code ON entries(group_code);
