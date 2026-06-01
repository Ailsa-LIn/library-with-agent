from __future__ import annotations

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "library.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed: bool = True) -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL UNIQUE,
                author TEXT DEFAULT '',
                category TEXT DEFAULT '',
                price REAL NOT NULL CHECK (price >= 0),
                stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                purchased_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                note TEXT DEFAULT '',
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                unit_price REAL NOT NULL CHECK (unit_price >= 0),
                total_price REAL NOT NULL CHECK (total_price >= 0),
                sold_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
            );
            """
        )

        if seed:
            count = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            if count == 0:
                conn.executemany(
                    """
                    INSERT INTO books (title, author, category, price, stock)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        ("数据结构", "严蔚敏", "计算机", 45.0, 30),
                        ("C++ Primer", "Stanley B. Lippman", "计算机", 99.0, 8),
                        ("Python 编程：从入门到实践", "Eric Matthes", "计算机", 89.0, 12),
                        ("活着", "余华", "文学", 39.0, 6),
                        ("高等数学", "同济大学数学系", "教材", 56.0, 20),
                    ],
                )


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]
