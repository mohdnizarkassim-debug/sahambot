import sqlite3
from datetime import date

DB_PATH = "sahambot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            tier        INTEGER DEFAULT 0,
            daily_usage INTEGER DEFAULT 0,
            last_reset  TEXT DEFAULT '',
            joined_date TEXT DEFAULT ''
        )
    ''')

    # Pilot tracking table — untuk review 3 bulan
    c.execute('''
        CREATE TABLE IF NOT EXISTS pilot_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            timeframe   TEXT,
            candle_count INTEGER,
            input_method TEXT,
            tier        INTEGER,
            timestamp   TEXT
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database ready.")

def get_user(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()

    if user:
        today = str(date.today())
        if user[4] != today:
            reset_daily_usage(user_id, today)
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = c.fetchone()
            conn.close()
    return user

def create_user(user_id: int, username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = str(date.today())
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, last_reset, joined_date) VALUES (?, ?, ?, ?)",
        (user_id, username, today, today)
    )
    conn.commit()
    conn.close()

def is_premium(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user[2] >= 1)

def increment_usage(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET daily_usage = daily_usage + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def reset_daily_usage(user_id: int, today: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET daily_usage = 0, last_reset = ? WHERE user_id = ?", (today, user_id))
    conn.commit()
    conn.close()

def set_tier(user_id: int, tier: int):
    """0=free, 1=premium, 2=pro"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET tier = ? WHERE user_id = ?", (tier, user_id))
    conn.commit()
    conn.close()

def log_pilot(user_id: int, timeframe: str, candle_count: int, input_method: str, tier: int):
    """Log setiap analisa untuk pilot review"""
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO pilot_log (user_id, timeframe, candle_count, input_method, tier, timestamp) VALUES (?,?,?,?,?,?)",
        (user_id, timeframe, candle_count, input_method, tier, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_pilot_stats():
    """Summary stats untuk pilot review"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    stats = {}

    c.execute("SELECT COUNT(*) FROM users")
    stats['total_users'] = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM users WHERE tier >= 1")
    stats['premium_users'] = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM pilot_log")
    stats['total_analyses'] = c.fetchone()[0]

    c.execute("SELECT timeframe, COUNT(*) FROM pilot_log GROUP BY timeframe ORDER BY COUNT(*) DESC")
    stats['timeframe_usage'] = c.fetchall()

    c.execute("SELECT candle_count, COUNT(*) FROM pilot_log GROUP BY candle_count ORDER BY COUNT(*) DESC")
    stats['candle_usage'] = c.fetchall()

    c.execute("SELECT input_method, COUNT(*) FROM pilot_log GROUP BY input_method")
    stats['input_method'] = c.fetchall()

    conn.close()
    return stats
