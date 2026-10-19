import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "study_planner.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                minutes INTEGER NOT NULL CHECK(minutes > 0),
                study_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_study_date
            ON study_sessions(study_date)
        """)

        # New table: this does not delete existing study sessions.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                due_date TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Medium'
                    CHECK(priority IN ('Low', 'Medium', 'High')),
                completed INTEGER NOT NULL DEFAULT 0
                    CHECK(completed IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_task_due_date
            ON tasks(due_date)
        """)


def get_all_sessions():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, subject, minutes,
                   study_date AS date, created_at
            FROM study_sessions
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


def add_session(subject, minutes, study_date):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO study_sessions (subject, minutes, study_date)
            VALUES (?, ?, ?)
        """, (subject, minutes, study_date))

        session_id = cursor.lastrowid

        row = connection.execute("""
            SELECT id, subject, minutes,
                   study_date AS date, created_at
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        return dict(row)


def update_session(session_id, subject, minutes, study_date):
    with get_connection() as connection:
        cursor = connection.execute("""
            UPDATE study_sessions
            SET subject = ?, minutes = ?, study_date = ?
            WHERE id = ?
        """, (subject, minutes, study_date, session_id))

        if cursor.rowcount == 0:
            return None

        row = connection.execute("""
            SELECT id, subject, minutes,
                   study_date AS date, created_at
            FROM study_sessions
            WHERE id = ?
        """, (session_id,)).fetchone()

        return dict(row)


def delete_session(session_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM study_sessions WHERE id = ?",
            (session_id,)
        )
        return cursor.rowcount > 0


def get_all_tasks():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, title, subject, due_date, priority,
                   completed, created_at
            FROM tasks
            ORDER BY completed ASC, due_date ASC, id DESC
        """).fetchall()

        tasks = []
        for row in rows:
            task = dict(row)
            task["completed"] = bool(task["completed"])
            tasks.append(task)

        return tasks


def add_task(title, subject, due_date, priority):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO tasks (title, subject, due_date, priority)
            VALUES (?, ?, ?, ?)
        """, (title, subject, due_date, priority))

        task_id = cursor.lastrowid

        row = connection.execute("""
            SELECT id, title, subject, due_date, priority,
                   completed, created_at
            FROM tasks
            WHERE id = ?
        """, (task_id,)).fetchone()

        task = dict(row)
        task["completed"] = bool(task["completed"])
        return task


def update_task(task_id, changes):
    allowed_columns = {
        "title", "subject", "due_date", "priority", "completed"
    }

    changes = {
        key: value
        for key, value in changes.items()
        if key in allowed_columns
    }

    if not changes:
        return get_task(task_id)

    if "completed" in changes:
        changes["completed"] = int(changes["completed"])

    assignments = ", ".join(
        f"{column} = ?" for column in changes
    )
    values = list(changes.values()) + [task_id]

    with get_connection() as connection:
        cursor = connection.execute(
            f"UPDATE tasks SET {assignments} WHERE id = ?",
            values
        )

        if cursor.rowcount == 0:
            return None

        row = connection.execute("""
            SELECT id, title, subject, due_date, priority,
                   completed, created_at
            FROM tasks
            WHERE id = ?
        """, (task_id,)).fetchone()

        task = dict(row)
        task["completed"] = bool(task["completed"])
        return task


def get_task(task_id):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT id, title, subject, due_date, priority,
                   completed, created_at
            FROM tasks
            WHERE id = ?
        """, (task_id,)).fetchone()

        if row is None:
            return None

        task = dict(row)
        task["completed"] = bool(task["completed"])
        return task


def delete_task(task_id):
    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id,)
        )
        return cursor.rowcount > 0


def get_subject_analytics():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT subject,
                   SUM(minutes) AS total_minutes,
                   COUNT(*) AS total_sessions,
                   MAX(study_date) AS last_studied
            FROM study_sessions
            GROUP BY subject
            ORDER BY total_minutes DESC
        """).fetchall()

        return [dict(row) for row in rows]


def get_daily_analytics(start_date, end_date):
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT study_date AS date,
                   SUM(minutes) AS total_minutes,
                   COUNT(*) AS total_sessions
            FROM study_sessions
            WHERE study_date BETWEEN ? AND ?
            GROUP BY study_date
            ORDER BY study_date
        """, (start_date, end_date)).fetchall()

        return [dict(row) for row in rows]