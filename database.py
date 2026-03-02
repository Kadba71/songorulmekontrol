import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", str(Path(__file__).with_name("bot_data.sqlite3"))))


def normalize_username(username: str) -> str:
    username = username.strip()
    if username.startswith("@"):
        username = username[1:]
    return username.lower()


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS responsibles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                threshold_minutes INTEGER,
                weekly_off_day TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                responsible_id INTEGER,
                department_id INTEGER,
                threshold_minutes INTEGER NOT NULL,
                day_off_date TEXT,
                exempt_until TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (responsible_id) REFERENCES responsibles(id) ON DELETE SET NULL,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS department_responsibles (
                department_id INTEGER NOT NULL,
                responsible_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (department_id, responsible_id),
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                FOREIGN KEY (responsible_id) REFERENCES responsibles(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_state (
                personnel_id INTEGER PRIMARY KEY,
                is_alerting INTEGER NOT NULL DEFAULT 0,
                last_notified_at TEXT,
                last_minutes INTEGER,
                last_status_text TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (personnel_id) REFERENCES personnel(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS violation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                personnel_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL,
                occurred_at TEXT NOT NULL,
                occurred_date TEXT NOT NULL,
                FOREIGN KEY (personnel_id) REFERENCES personnel(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_violation_events_date_personnel
            ON violation_events(occurred_date, personnel_id)
            """
        )
        _ensure_column(conn, "departments", "threshold_minutes", "INTEGER")
        _ensure_column(conn, "departments", "weekly_off_day", "TEXT")
        _ensure_column(conn, "personnel", "day_off_date", "TEXT")
        _ensure_column(conn, "personnel", "exempt_until", "TEXT")


def _ensure_column(conn: sqlite3.Connection, table_name: str, column_name: str, sql_type: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    col_names = {str(row[1]) for row in cols}
    if column_name not in col_names:
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}")


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_responsible(username: str) -> str:
    username = normalize_username(username)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO responsibles(username, created_at) VALUES(?, ?)",
            (username, _utcnow_iso()),
        )
    return username


def remove_responsible(username: str) -> bool:
    username = normalize_username(username)
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM responsibles WHERE username = ?", (username,))
        return cur.rowcount > 0


def add_department(name: str) -> str:
    name = name.strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO departments(name, created_at) VALUES(?, ?)",
            (name, _utcnow_iso()),
        )
    return name


def set_department_threshold(name: str, minutes: int) -> str:
    name = name.strip()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO departments(name, created_at) VALUES(?, ?)",
            (name, _utcnow_iso()),
        )
        conn.execute(
            "UPDATE departments SET threshold_minutes = ? WHERE name = ?",
            (minutes, name),
        )
    return name


def set_department_weekly_off(name: str, weekly_off_day: str) -> str:
    name = name.strip()
    weekly_off_day = weekly_off_day.strip().lower()
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO departments(name, created_at) VALUES(?, ?)",
            (name, _utcnow_iso()),
        )
        conn.execute(
            "UPDATE departments SET weekly_off_day = ? WHERE name = ?",
            (weekly_off_day, name),
        )
    return name


def remove_department(name: str) -> bool:
    name = name.strip()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM departments WHERE name = ?", (name,))
        return cur.rowcount > 0


def add_department_responsible(department_name: str, responsible_username: str) -> tuple[str, str]:
    with get_conn() as conn:
        department_id = _get_department_id(conn, department_name)
        responsible_id = _get_responsible_id(conn, responsible_username)
        conn.execute(
            """
            INSERT OR IGNORE INTO department_responsibles(department_id, responsible_id, created_at)
            VALUES(?, ?, ?)
            """,
            (department_id, responsible_id, _utcnow_iso()),
        )
    return department_name.strip(), normalize_username(responsible_username)


def remove_department_responsible(department_name: str, responsible_username: str) -> bool:
    department_name = department_name.strip()
    responsible_username = normalize_username(responsible_username)
    with get_conn() as conn:
        dep_row = conn.execute("SELECT id FROM departments WHERE name = ?", (department_name,)).fetchone()
        rsp_row = conn.execute("SELECT id FROM responsibles WHERE username = ?", (responsible_username,)).fetchone()
        if dep_row is None or rsp_row is None:
            return False
        cur = conn.execute(
            "DELETE FROM department_responsibles WHERE department_id = ? AND responsible_id = ?",
            (int(dep_row["id"]), int(rsp_row["id"])),
        )
        return cur.rowcount > 0


def _get_responsible_id(conn: sqlite3.Connection, username: str) -> int:
    username = normalize_username(username)
    conn.execute(
        "INSERT OR IGNORE INTO responsibles(username, created_at) VALUES(?, ?)",
        (username, _utcnow_iso()),
    )
    row = conn.execute("SELECT id FROM responsibles WHERE username = ?", (username,)).fetchone()
    return int(row["id"])


def _get_department_id(conn: sqlite3.Connection, name: str) -> int:
    name = name.strip()
    conn.execute(
        "INSERT OR IGNORE INTO departments(name, created_at) VALUES(?, ?)",
        (name, _utcnow_iso()),
    )
    row = conn.execute("SELECT id FROM departments WHERE name = ?", (name,)).fetchone()
    return int(row["id"])


def add_personnel(username: str, responsible_username: str, department_name: str) -> str:
    username = normalize_username(username)
    with get_conn() as conn:
        responsible_id = _get_responsible_id(conn, responsible_username)
        department_id = _get_department_id(conn, department_name)
        conn.execute(
            """
            INSERT INTO personnel(username, responsible_id, department_id, threshold_minutes, active, created_at)
            VALUES(?, ?, ?, ?, 1, ?)
            ON CONFLICT(username) DO UPDATE SET
                responsible_id = excluded.responsible_id,
                department_id = excluded.department_id,
                threshold_minutes = threshold_minutes,
                day_off_date = NULL,
                exempt_until = NULL,
                active = 1
            """,
            (username, responsible_id, department_id, 0, _utcnow_iso()),
        )
    return username


def remove_personnel(username: str) -> bool:
    username = normalize_username(username)
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM personnel WHERE username = ?", (username,))
        return cur.rowcount > 0


def list_personnel() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT
                p.id,
                p.username,
                p.threshold_minutes,
                p.day_off_date,
                p.exempt_until,
                r.username AS responsible_username,
                d.id AS department_id,
                d.name AS department_name,
                d.threshold_minutes AS department_threshold_minutes,
                d.weekly_off_day AS department_weekly_off_day
            FROM personnel p
            LEFT JOIN responsibles r ON p.responsible_id = r.id
            LEFT JOIN departments d ON p.department_id = d.id
            WHERE p.active = 1
            ORDER BY p.username
            """
        ).fetchall()


def get_department_responsibles(department_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT r.username
            FROM department_responsibles dr
            JOIN responsibles r ON r.id = dr.responsible_id
            WHERE dr.department_id = ?
            ORDER BY r.username
            """,
            (department_id,),
        ).fetchall()
    return [str(row["username"]) for row in rows]


def set_personnel_day_off_today(username: str, today_iso: str) -> bool:
    username = normalize_username(username)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE personnel SET day_off_date = ?, exempt_until = NULL WHERE username = ?",
            (today_iso, username),
        )
        return cur.rowcount > 0


def set_personnel_hourly_off(username: str, until_iso: str) -> bool:
    username = normalize_username(username)
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE personnel SET exempt_until = ?, day_off_date = NULL WHERE username = ?",
            (until_iso, username),
        )
        return cur.rowcount > 0


def get_watch_state(personnel_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM watch_state WHERE personnel_id = ?",
            (personnel_id,),
        ).fetchone()


def set_watch_state(
    personnel_id: int,
    is_alerting: bool,
    last_notified_at: str | None,
    last_minutes: int | None,
    last_status_text: str,
) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO watch_state(personnel_id, is_alerting, last_notified_at, last_minutes, last_status_text, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(personnel_id) DO UPDATE SET
                is_alerting = excluded.is_alerting,
                last_notified_at = excluded.last_notified_at,
                last_minutes = excluded.last_minutes,
                last_status_text = excluded.last_status_text,
                updated_at = excluded.updated_at
            """,
            (
                personnel_id,
                1 if is_alerting else 0,
                last_notified_at,
                last_minutes,
                last_status_text,
                _utcnow_iso(),
            ),
        )


def add_violation_event(personnel_id: int, minutes: int, occurred_at_iso: str, occurred_date: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO violation_events(personnel_id, minutes, occurred_at, occurred_date)
            VALUES(?, ?, ?, ?)
            """,
            (personnel_id, minutes, occurred_at_iso, occurred_date),
        )


def get_daily_violation_counts(occurred_date: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            """
            SELECT
                d.id AS department_id,
                d.name AS department_name,
                p.username AS personnel_username,
                r.username AS responsible_username,
                COUNT(ve.id) AS violation_count
            FROM violation_events ve
            JOIN personnel p ON p.id = ve.personnel_id
            LEFT JOIN departments d ON d.id = p.department_id
            LEFT JOIN responsibles r ON r.id = p.responsible_id
            WHERE ve.occurred_date = ?
            GROUP BY d.id, d.name, p.username, r.username
            ORDER BY d.name, p.username
            """,
            (occurred_date,),
        ).fetchall()
