"""
لایه‌ی دیتابیس (SQLite) - کاربرها، پلن‌ها، سفارش‌ها، تراکنش‌های کیف پول
"""
import sqlite3
import time
from contextlib import closing

from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(get_conn()) as conn, conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                balance INTEGER NOT NULL DEFAULT 0,
                referrer_id INTEGER,
                joined_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,       -- مثلا: "🇩🇪 آلمان", "🇫🇮 فنلاند"
                duration_days INTEGER NOT NULL,
                traffic_gb INTEGER NOT NULL,
                price INTEGER NOT NULL,       -- تومان
                is_active INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                plan_id INTEGER NOT NULL REFERENCES plans(id),
                config_text TEXT,
                status TEXT NOT NULL DEFAULT 'active',  -- active/expired
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                amount INTEGER NOT NULL,
                kind TEXT NOT NULL,             -- 'charge' | 'purchase' | 'referral' | 'admin'
                status TEXT NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
                note TEXT,
                created_at INTEGER NOT NULL
            )
        """)
        # چند پلن نمونه برای شروع - از پنل ادمین می‌تونی مدیریتشون کنی
        cur = conn.execute("SELECT COUNT(*) AS c FROM plans")
        if cur.fetchone()["c"] == 0:
            sample = [
                ("۱ ماهه - ۳۰ گیگ", "🇩🇪 آلمان", 30, 30, 90000),
                ("۱ ماهه - نامحدود", "🇩🇪 آلمان", 30, 0, 150000),
                ("۱ ماهه - ۳۰ گیگ", "🇫🇮 فنلاند", 30, 30, 95000),
                ("۳ ماهه - ۹۰ گیگ", "🇳🇱 هلند", 90, 90, 250000),
            ]
            conn.executemany(
                "INSERT INTO plans (title, category, duration_days, traffic_gb, price) "
                "VALUES (?,?,?,?,?)",
                sample,
            )


# ------------------------- کاربرها -------------------------

def get_or_create_user(telegram_id: int, username: str, first_name: str, referrer_tid: int | None = None):
    with closing(get_conn()) as conn, conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        if row:
            return dict(row)
        referrer_id = None
        if referrer_tid and referrer_tid != telegram_id:
            ref_row = conn.execute("SELECT id FROM users WHERE telegram_id=?", (referrer_tid,)).fetchone()
            if ref_row:
                referrer_id = ref_row["id"]
        conn.execute(
            "INSERT INTO users (telegram_id, username, first_name, balance, referrer_id, joined_at) "
            "VALUES (?,?,?,0,?,?)",
            (telegram_id, username, first_name, referrer_id, int(time.time())),
        )
        row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        return dict(row)


def get_user_by_tid(telegram_id: int):
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,)).fetchone()
        return dict(row) if row else None


def change_balance(user_id: int, delta: int):
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE id=?", (delta, user_id))


def count_referrals(user_id: int) -> int:
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT COUNT(*) c FROM users WHERE referrer_id=?", (user_id,)).fetchone()
        return row["c"]


# ------------------------- پلن‌ها -------------------------

def list_categories():
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM plans WHERE is_active=1 ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


def list_plans_by_category(category: str):
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM plans WHERE category=? AND is_active=1 ORDER BY price", (category,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_plan(plan_id: int):
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
        return dict(row) if row else None


def add_plan(title, category, duration_days, traffic_gb, price):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO plans (title, category, duration_days, traffic_gb, price) VALUES (?,?,?,?,?)",
            (title, category, duration_days, traffic_gb, price),
        )


# ------------------------- سفارش‌ها -------------------------

def create_order(user_id: int, plan_id: int, config_text: str, duration_days: int):
    now = int(time.time())
    expires_at = now + duration_days * 86400
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO orders (user_id, plan_id, config_text, created_at, expires_at) "
            "VALUES (?,?,?,?,?)",
            (user_id, plan_id, config_text, now, expires_at),
        )
        return conn.execute("SELECT last_insert_rowid() id").fetchone()["id"]


def list_user_orders(user_id: int):
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT o.*, p.title, p.category FROM orders o "
            "JOIN plans p ON p.id = o.plan_id "
            "WHERE o.user_id=? ORDER BY o.created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ------------------------- تراکنش‌ها (شارژ کیف پول) -------------------------

def add_transaction(user_id: int, amount: int, kind: str, note: str = "", status: str = "pending"):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO transactions (user_id, amount, kind, status, note, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, amount, kind, status, note, int(time.time())),
        )
        return conn.execute("SELECT last_insert_rowid() id").fetchone()["id"]


def get_transaction(tx_id: int):
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()
        return dict(row) if row else None


def set_transaction_status(tx_id: int, status: str):
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE transactions SET status=? WHERE id=?", (status, tx_id))
