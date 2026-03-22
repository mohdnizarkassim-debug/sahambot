import logging
import sqlite3
from datetime import date

DB_PATH = "sahambot.db"
logger = logging.getLogger(__name__)


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_users_table_sql(table_name: str, if_not_exists: bool = False) -> str:
    clause = "IF NOT EXISTS " if if_not_exists else ""
    return f'''
        CREATE TABLE {clause}{table_name} (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            tier        INTEGER DEFAULT 0 CHECK (tier IN (0, 1, 2)),
            daily_usage INTEGER DEFAULT 0 CHECK (daily_usage >= 0),
            last_reset  TEXT DEFAULT '',
            joined_date TEXT DEFAULT ''
        )
    '''


def _create_pilot_log_table_sql(table_name: str, if_not_exists: bool = False) -> str:
    clause = "IF NOT EXISTS " if if_not_exists else ""
    return f'''
        CREATE TABLE {clause}{table_name} (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER,
            timeframe    TEXT,
            candle_count INTEGER,
            input_method TEXT,
            tier         INTEGER,
            timestamp    TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    '''


def _table_sql(conn, table_name: str):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row[0] if row else ""


def _migrate_users_table(conn):
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP TABLE IF EXISTS users_new")
    conn.execute(_create_users_table_sql("users_new"))
    conn.execute(
        """
        INSERT INTO users_new (user_id, username, tier, daily_usage, last_reset, joined_date)
        SELECT
            user_id,
            username,
            CASE WHEN tier IN (0, 1, 2) THEN tier ELSE 0 END,
            CASE WHEN daily_usage >= 0 THEN daily_usage ELSE 0 END,
            COALESCE(last_reset, ''),
            COALESCE(joined_date, '')
        FROM users
        """
    )
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_new RENAME TO users")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def _migrate_pilot_log_table(conn):
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("DROP TABLE IF EXISTS pilot_log_new")
    conn.execute(_create_pilot_log_table_sql("pilot_log_new"))
    conn.execute(
        """
        INSERT INTO pilot_log_new (id, user_id, timeframe, candle_count, input_method, tier, timestamp)
        SELECT
            p.id,
            p.user_id,
            p.timeframe,
            p.candle_count,
            p.input_method,
            p.tier,
            p.timestamp
        FROM pilot_log p
        LEFT JOIN users u ON u.user_id = p.user_id
        WHERE p.user_id IS NULL OR u.user_id IS NOT NULL
        """
    )
    conn.execute("DROP TABLE pilot_log")
    conn.execute("ALTER TABLE pilot_log_new RENAME TO pilot_log")
    conn.commit()
    conn.execute("PRAGMA foreign_keys = ON")


def init_db():
    conn = get_connection()
    try:
        conn.execute(_create_users_table_sql("users", if_not_exists=True))
        conn.execute(_create_pilot_log_table_sql("pilot_log", if_not_exists=True))

        users_sql = _table_sql(conn, "users").upper()
        if "CHECK (TIER IN (0, 1, 2))" not in users_sql or "CHECK (DAILY_USAGE >= 0)" not in users_sql:
            _migrate_users_table(conn)

        pilot_log_sql = _table_sql(conn, "pilot_log").upper()
        if "FOREIGN KEY (USER_ID) REFERENCES USERS(USER_ID)" not in pilot_log_sql:
            _migrate_pilot_log_table(conn)

        conn.commit()
    finally:
        conn.close()

    logger.info("Database ready")


def get_user(user_id: int):
    conn = get_connection()
    try:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def ensure_daily_usage_current(user_id: int):
    today = str(date.today())
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE users
            SET daily_usage = CASE WHEN last_reset = ? THEN daily_usage ELSE 0 END,
                last_reset = ?
            WHERE user_id = ?
            """,
            (today, today, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def create_user(user_id: int, username: str):
    conn = get_connection()
    today = str(date.today())
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, last_reset, joined_date) VALUES (?, ?, ?, ?)",
            (user_id, username, today, today)
        )
        conn.commit()
    finally:
        conn.close()


def is_premium(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user[2] >= 1)


def increment_usage(user_id: int):
    today = str(date.today())
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            UPDATE users
            SET daily_usage = CASE WHEN last_reset = ? THEN daily_usage + 1 ELSE 1 END,
                last_reset = ?
            WHERE user_id = ?
            """,
            (today, today, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def reset_daily_usage(user_id: int, today: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET daily_usage = 0, last_reset = ? WHERE user_id = ?", (today, user_id))
        conn.commit()
    finally:
        conn.close()


def set_tier(user_id: int, tier: int):
    """0=free, 1=premium, 2=pro"""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET tier = ? WHERE user_id = ?", (tier, user_id))
        conn.commit()
    finally:
        conn.close()


def log_pilot(user_id: int, timeframe: str, candle_count: int, input_method: str, tier: int):
    """Log setiap analisa untuk pilot review"""
    from datetime import datetime

    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO pilot_log (user_id, timeframe, candle_count, input_method, tier, timestamp) VALUES (?,?,?,?,?,?)",
            (user_id, timeframe, candle_count, input_method, tier, datetime.now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_pilot_stats():
    """Summary stats untuk pilot review"""
    conn = get_connection()

    try:
        stats = {}

        stats['total_users'] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        stats['premium_users'] = conn.execute("SELECT COUNT(*) FROM users WHERE tier >= 1").fetchone()[0]
        stats['total_analyses'] = conn.execute("SELECT COUNT(*) FROM pilot_log").fetchone()[0]
        stats['timeframe_usage'] = conn.execute(
            "SELECT timeframe, COUNT(*) FROM pilot_log GROUP BY timeframe ORDER BY COUNT(*) DESC"
        ).fetchall()
        stats['candle_usage'] = conn.execute(
            "SELECT candle_count, COUNT(*) FROM pilot_log GROUP BY candle_count ORDER BY COUNT(*) DESC"
        ).fetchall()
        stats['input_method'] = conn.execute(
            "SELECT input_method, COUNT(*) FROM pilot_log GROUP BY input_method"
        ).fetchall()

        return stats
    finally:
        conn.close()