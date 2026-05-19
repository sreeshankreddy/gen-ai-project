import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.auth_password import hash_password, verify_password

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "notes.db"


class NotesDatabase:
  def __init__(self, db_path: Path | str | None = None) -> None:
    self.db_path = Path(db_path) if db_path else DB_PATH
    self.db_path.parent.mkdir(parents=True, exist_ok=True)
    self._init_db()

  def _connect(self) -> sqlite3.Connection:
    conn = sqlite3.connect(self.db_path)
    conn.row_factory = sqlite3.Row
    return conn

  def _migrate_notes_user_id(self, conn: sqlite3.Connection) -> None:
    cols = [row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()]
    if "user_id" not in cols:
      conn.execute("ALTER TABLE notes ADD COLUMN user_id INTEGER REFERENCES users(id)")

  def _init_db(self) -> None:
    with self._connect() as conn:
      conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL COLLATE NOCASE UNIQUE,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
      )
      conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER REFERENCES users(id),
          title TEXT NOT NULL,
          source_type TEXT NOT NULL,
          raw_content TEXT NOT NULL,
          short_summary TEXT,
          key_points TEXT,
          chapter_summary TEXT,
          practice_questions TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
      )
      conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expenses (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER REFERENCES users(id),
          description TEXT NOT NULL,
          amount REAL NOT NULL,
          category TEXT NOT NULL,
          expense_date TEXT NOT NULL,
          notes TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL
        )
        """
      )
      self._migrate_notes_user_id(conn)

  def username_exists(self, username: str) -> bool:
    with self._connect() as conn:
      row = conn.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username.strip(),),
      ).fetchone()
    return row is not None

  def register_user(self, username: str, password: str) -> int | None:
    username = username.strip()
    if not username or not password:
      return None
    if self.username_exists(username):
      return None
    now = datetime.now(timezone.utc).isoformat()
    pw_hash = hash_password(password)
    with self._connect() as conn:
      try:
        cursor = conn.execute(
          "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
          (username, pw_hash, now),
        )
        return int(cursor.lastrowid)
      except sqlite3.IntegrityError:
        return None

  def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
    username = username.strip()
    if not username or not password:
      return None
    with self._connect() as conn:
      row = conn.execute(
        "SELECT id, username, password_hash FROM users WHERE username = ?",
        (username,),
      ).fetchone()
    if not row:
      return None
    if not verify_password(password, row["password_hash"]):
      return None
    return {"id": int(row["id"]), "username": row["username"]}

  def create(
    self,
    title: str,
    source_type: str,
    raw_content: str,
    user_id: int,
    short_summary: str = "",
    key_points: str = "",
    chapter_summary: str = "",
    practice_questions: str = "",
  ) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with self._connect() as conn:
      cursor = conn.execute(
        """
        INSERT INTO notes (
          user_id, title, source_type, raw_content, short_summary, key_points,
          chapter_summary, practice_questions, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          user_id,
          title,
          source_type,
          raw_content,
          short_summary,
          key_points,
          chapter_summary,
          practice_questions,
          now,
          now,
        ),
      )
      return int(cursor.lastrowid)

  def read_all(self, user_id: int) -> list[dict[str, Any]]:
    with self._connect() as conn:
      rows = conn.execute(
        "SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
      ).fetchall()
    return [dict(row) for row in rows]

  def read_one(self, note_id: int, user_id: int) -> dict[str, Any] | None:
    with self._connect() as conn:
      row = conn.execute(
        "SELECT * FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id),
      ).fetchone()
    return dict(row) if row else None

  def update(
    self,
    note_id: int,
    user_id: int,
    *,
    title: str | None = None,
    short_summary: str | None = None,
    key_points: str | None = None,
    chapter_summary: str | None = None,
    practice_questions: str | None = None,
    raw_content: str | None = None,
  ) -> bool:
    existing = self.read_one(note_id, user_id)
    if not existing:
      return False

    fields = {
      "title": title if title is not None else existing["title"],
      "short_summary": short_summary if short_summary is not None else existing["short_summary"],
      "key_points": key_points if key_points is not None else existing["key_points"],
      "chapter_summary": chapter_summary if chapter_summary is not None else existing["chapter_summary"],
      "practice_questions": practice_questions if practice_questions is not None else existing["practice_questions"],
      "raw_content": raw_content if raw_content is not None else existing["raw_content"],
    }
    now = datetime.now(timezone.utc).isoformat()

    with self._connect() as conn:
      conn.execute(
        """
        UPDATE notes SET
          title = ?, short_summary = ?, key_points = ?,
          chapter_summary = ?, practice_questions = ?, raw_content = ?,
          updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
          fields["title"],
          fields["short_summary"],
          fields["key_points"],
          fields["chapter_summary"],
          fields["practice_questions"],
          fields["raw_content"],
          now,
          note_id,
          user_id,
        ),
      )
    return True

  def delete(self, note_id: int, user_id: int) -> bool:
    with self._connect() as conn:
      cursor = conn.execute(
        "DELETE FROM notes WHERE id = ? AND user_id = ?",
        (note_id, user_id),
      )
      return cursor.rowcount > 0

  def create_expense(
    self,
    user_id: int,
    description: str,
    amount: float,
    category: str,
    expense_date: str,
    notes: str = "",
  ) -> int:
    now = datetime.now(timezone.utc).isoformat()
    with self._connect() as conn:
      cursor = conn.execute(
        """
        INSERT INTO expenses (
          user_id, description, amount, category, expense_date, notes,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          user_id,
          description.strip(),
          amount,
          category.strip(),
          expense_date,
          notes.strip(),
          now,
          now,
        ),
      )
      return int(cursor.lastrowid)

  def read_expenses(self, user_id: int) -> list[dict[str, Any]]:
    with self._connect() as conn:
      rows = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY expense_date DESC, updated_at DESC",
        (user_id,),
      ).fetchall()
    return [dict(row) for row in rows]

  def update_expense(
    self,
    expense_id: int,
    user_id: int,
    *,
    description: str | None = None,
    amount: float | None = None,
    category: str | None = None,
    expense_date: str | None = None,
    notes: str | None = None,
  ) -> bool:
    existing = self.read_expenses(user_id)
    expense = next((e for e in existing if e["id"] == expense_id), None)
    if not expense:
      return False

    fields = {
      "description": description if description is not None else expense["description"],
      "amount": amount if amount is not None else expense["amount"],
      "category": category if category is not None else expense["category"],
      "expense_date": expense_date if expense_date is not None else expense["expense_date"],
      "notes": notes if notes is not None else expense["notes"],
    }
    now = datetime.now(timezone.utc).isoformat()
    with self._connect() as conn:
      conn.execute(
        """
        UPDATE expenses SET
          description = ?, amount = ?, category = ?, expense_date = ?,
          notes = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
          fields["description"],
          fields["amount"],
          fields["category"],
          fields["expense_date"],
          fields["notes"],
          now,
          expense_id,
          user_id,
        ),
      )
    return True

  def delete_expense(self, expense_id: int, user_id: int) -> bool:
    with self._connect() as conn:
      cursor = conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
      )
      return cursor.rowcount > 0
