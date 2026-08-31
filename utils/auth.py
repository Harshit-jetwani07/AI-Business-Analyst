import sqlite3
import hashlib
import secrets
import os
from datetime import datetime, timedelta

DB_PATH = "data/users.db"
PBKDF2_ITERATIONS = 260_000
MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_MINUTES = 15
DEMO_USERNAME = "demo_user"
DEMO_EMAIL = "demo@bizvision.ai"
DEMO_PASSWORD = "BizVision@2026"


def _hash(password: str, salt: str) -> str:
    """Legacy hash kept for existing databases created before PBKDF2 support."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return salt, f"pbkdf2_sha256${PBKDF2_ITERATIONS}${digest}"


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, digest = stored_hash.split("$", 2)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return secrets.compare_digest(candidate, digest)
        except Exception:
            return False
    return secrets.compare_digest(_hash(password, salt), stored_hash)


def get_conn():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and seed default admin + demo user."""
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            salt      TEXT NOT NULL,
            password  TEXT NOT NULL,
            role      TEXT NOT NULL DEFAULT 'user',
            active    INTEGER NOT NULL DEFAULT 1,
            created   TEXT NOT NULL,
            last_login TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT NOT NULL,
            action    TEXT NOT NULL,
            detail    TEXT,
            timestamp TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS datasets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            uploaded_by TEXT NOT NULL,
            rows        INTEGER,
            cols        INTEGER,
            file_path   TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            admin_notes TEXT DEFAULT '',
            quality_score INTEGER DEFAULT 0,
            quality_grade TEXT DEFAULT '',
            approved    INTEGER DEFAULT 0,
            status      TEXT DEFAULT 'pending',
            created     TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            created_by  TEXT NOT NULL,
            approved    INTEGER DEFAULT 0,
            admin_notes TEXT DEFAULT '',
            created     TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS login_attempts (
            username     TEXT PRIMARY KEY,
            failed_count INTEGER NOT NULL DEFAULT 0,
            locked_until TEXT,
            last_failed  TEXT
        )
    """)

    conn.commit()

    _ensure_column(c, "datasets", "file_path", "TEXT DEFAULT ''")
    _ensure_column(c, "datasets", "admin_notes", "TEXT DEFAULT ''")
    _ensure_column(c, "datasets", "quality_score", "INTEGER DEFAULT 0")
    _ensure_column(c, "datasets", "quality_grade", "TEXT DEFAULT ''")
    _ensure_column(c, "datasets", "status", "TEXT DEFAULT 'pending'")
    _ensure_column(c, "reports", "status", "TEXT DEFAULT 'pending'")
    c.execute("UPDATE datasets SET status='approved' WHERE approved=1 AND (status IS NULL OR status='pending')")
    c.execute("UPDATE reports SET status='approved' WHERE approved=1 AND (status IS NULL OR status='pending')")
    conn.commit()

    # Demo accounts are opt-in so public deployments do not accidentally expose default logins.
    if c.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        initial_password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
        if initial_password:
            _create_user_raw(
                c,
                os.getenv("INITIAL_ADMIN_USERNAME", "admin"),
                os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com"),
                initial_password,
                "admin",
            )
            conn.commit()
        else:
            allow_demo = os.getenv("ALLOW_DEMO_CREDENTIALS", "").lower() in {"1", "true", "yes"}
            if allow_demo:
                demo_admin_password = os.getenv("DEMO_ADMIN_PASSWORD", "")
                demo_user_password = os.getenv("DEMO_USER_PASSWORD", "")
                if demo_admin_password and demo_user_password:
                    _create_user_raw(c, "admin",    "admin@bizai.com",    demo_admin_password,   "admin")
                    _create_user_raw(c, "demouser", "user@bizai.com",     demo_user_password,    "user")
                    conn.commit()

    if os.getenv("DISABLE_PORTFOLIO_DEMO_ACCOUNT", "").lower() not in {"1", "true", "yes"}:
        _ensure_demo_user(c)
        conn.commit()

    conn.close()


def _ensure_column(cursor, table: str, column: str, definition: str):
    existing = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _create_user_raw(cursor, username, email, password, role):
    salt, hashed = hash_password(password)
    cursor.execute(
        "INSERT INTO users (username,email,salt,password,role,active,created) VALUES (?,?,?,?,?,1,?)",
        (username, email, salt, hashed, role, datetime.now().isoformat())
    )


def _ensure_demo_user(cursor):
    salt, hashed = hash_password(DEMO_PASSWORD)
    existing = cursor.execute(
        "SELECT id FROM users WHERE lower(username)=lower(?) OR lower(email)=lower(?)",
        (DEMO_USERNAME, DEMO_EMAIL),
    ).fetchone()
    if existing:
        cursor.execute(
            """UPDATE users
               SET username=?, email=?, salt=?, password=?, role='user', active=1
               WHERE id=?""",
            (DEMO_USERNAME, DEMO_EMAIL, salt, hashed, existing["id"]),
        )
    else:
        _create_user_raw(cursor, DEMO_USERNAME, DEMO_EMAIL, DEMO_PASSWORD, "user")

    cursor.execute("DELETE FROM login_attempts WHERE lower(username)=lower(?)", (DEMO_USERNAME,))


def get_login_lock(username: str):
    conn = get_conn()
    row = conn.execute(
        "SELECT failed_count, locked_until FROM login_attempts WHERE lower(username)=lower(?)",
        (username.strip(),),
    ).fetchone()
    conn.close()
    if not row or not row["locked_until"]:
        return None
    try:
        locked_until = datetime.fromisoformat(row["locked_until"])
    except ValueError:
        return None
    if locked_until <= datetime.now():
        clear_login_failures(username)
        return None
    return locked_until


def record_login_failure(username: str):
    username = username.strip().lower()
    if not username:
        return
    conn = get_conn()
    row = conn.execute(
        "SELECT failed_count FROM login_attempts WHERE username=?",
        (username,),
    ).fetchone()
    failed_count = int(row["failed_count"]) + 1 if row else 1
    locked_until = None
    if failed_count >= MAX_LOGIN_FAILURES:
        locked_until = (datetime.now() + timedelta(minutes=LOGIN_LOCK_MINUTES)).isoformat()
    conn.execute(
        """INSERT INTO login_attempts (username, failed_count, locked_until, last_failed)
           VALUES (?,?,?,?)
           ON CONFLICT(username) DO UPDATE SET
             failed_count=excluded.failed_count,
             locked_until=excluded.locked_until,
             last_failed=excluded.last_failed""",
        (username, failed_count, locked_until, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def clear_login_failures(username: str):
    conn = get_conn()
    conn.execute("DELETE FROM login_attempts WHERE lower(username)=lower(?)", (username.strip(),))
    conn.commit()
    conn.close()


#  Public API 

def authenticate(username: str, password: str):
    """Return user row dict or None."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=? AND active=1", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    if verify_password(password, row["salt"], row["password"]):
        # update last_login
        conn2 = get_conn()
        last_login = datetime.now().isoformat()
        if not row["password"].startswith("pbkdf2_sha256$"):
            new_salt, new_hash = hash_password(password)
            conn2.execute(
                "UPDATE users SET last_login=?, salt=?, password=? WHERE username=?",
                (last_login, new_salt, new_hash, username),
            )
        else:
            conn2.execute("UPDATE users SET last_login=? WHERE username=?",
                          (last_login, username))
        conn2.commit()
        conn2.close()
        return dict(row)
    return None


def create_user(username: str, email: str, password: str, role: str = "user") -> bool:
    try:
        conn = get_conn()
        salt, hashed = hash_password(password)
        conn.execute(
            "INSERT INTO users (username,email,salt,password,role,active,created) VALUES (?,?,?,?,?,1,?)",
            (username, email, salt, hashed, role, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_all_users():
    conn = get_conn()
    rows = conn.execute("SELECT id,username,email,role,active,created,last_login FROM users ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_user_role(user_id: int, role: str):
    conn = get_conn()
    conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
    conn.commit()
    conn.close()


def toggle_user_active(user_id: int):
    conn = get_conn()
    conn.execute("UPDATE users SET active = 1 - active WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def delete_user(user_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def log_activity(username: str, action: str, detail: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO activity_log (username,action,detail,timestamp) VALUES (?,?,?,?)",
        (username, action, detail, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_activity_log(limit: int = 100):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_dataset_record(name, uploaded_by, rows, cols, file_path="", quality_score=0, quality_grade=""):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO datasets
           (name,uploaded_by,rows,cols,file_path,quality_score,quality_grade,status,created)
           VALUES (?,?,?,?,?,?,?,'pending',?)""",
        (name, uploaded_by, rows, cols, file_path, quality_score, quality_grade, datetime.now().isoformat())
    )
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id


def get_all_datasets():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM datasets ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_datasets(username: str):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM datasets WHERE uploaded_by=? ORDER BY id DESC", (username,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_dataset_record(dataset_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_dataset_notes(dataset_id, notes):
    conn = get_conn()
    conn.execute("UPDATE datasets SET notes=? WHERE id=?", (notes, dataset_id))
    conn.commit()
    conn.close()


def update_dataset_review(dataset_id, status, admin_notes=""):
    conn = get_conn()
    approved = 1 if status == "approved" else 0
    conn.execute(
        "UPDATE datasets SET status=?, approved=?, admin_notes=? WHERE id=?",
        (status, approved, admin_notes, dataset_id)
    )
    conn.commit()
    conn.close()


def approve_dataset(dataset_id, admin_notes=""):
    update_dataset_review(dataset_id, "approved", admin_notes)


def reject_dataset(dataset_id, admin_notes=""):
    update_dataset_review(dataset_id, "rejected", admin_notes)


def delete_dataset_record(dataset_id):
    conn = get_conn()
    conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    conn.commit()
    conn.close()


def save_report_record(title, created_by):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO reports (title,created_by,created) VALUES (?,?,?)",
        (title, created_by, datetime.now().isoformat())
    )
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id


def get_all_reports():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM reports ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_report(report_id, admin_notes=""):
    conn = get_conn()
    conn.execute(
        "UPDATE reports SET approved=1, status='approved', admin_notes=? WHERE id=?",
        (admin_notes, report_id)
    )
    conn.commit()
    conn.close()


def reject_report(report_id, admin_notes=""):
    conn = get_conn()
    conn.execute(
        "UPDATE reports SET approved=0, status='rejected', admin_notes=? WHERE id=?",
        (admin_notes, report_id)
    )
    conn.commit()
    conn.close()


def update_report_notes(report_id, notes):
    conn = get_conn()
    conn.execute("UPDATE reports SET admin_notes=? WHERE id=?", (notes, report_id))
    conn.commit()
    conn.close()


def get_admin_metrics():
    conn = get_conn()
    metrics = {
        "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "active_users": conn.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0],
        "datasets": conn.execute("SELECT COUNT(*) FROM datasets").fetchone()[0],
        "pending_datasets": conn.execute("SELECT COUNT(*) FROM datasets WHERE status='pending'").fetchone()[0],
        "reports": conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
        "pending_reports": conn.execute("SELECT COUNT(*) FROM reports WHERE COALESCE(status,'pending')='pending'").fetchone()[0],
        "ai_queries": conn.execute("SELECT COUNT(*) FROM activity_log WHERE action='AI Query'").fetchone()[0],
        "uploads": conn.execute("SELECT COUNT(*) FROM activity_log WHERE action IN ('Upload Dataset','Load Sample Data')").fetchone()[0],
    }
    top_user = conn.execute(
        """SELECT username, COUNT(*) AS total
           FROM activity_log
           GROUP BY username
           ORDER BY total DESC
           LIMIT 1"""
    ).fetchone()
    metrics["top_user"] = dict(top_user) if top_user else {"username": "N/A", "total": 0}
    conn.close()
    return metrics


def get_user_activity(username: str, limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM activity_log WHERE username=? ORDER BY id DESC LIMIT ?",
        (username, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

