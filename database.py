import sqlite3
import config


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            owner_name TEXT,
            city TEXT,
            state TEXT,
            industry TEXT,
            website_url TEXT,
            phone TEXT,
            email TEXT,
            stage TEXT DEFAULT 'researched',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id),
            type TEXT,
            outcome TEXT,
            opener_used TEXT,
            objections TEXT,
            cta_used TEXT,
            cta_response TEXT,
            notes TEXT,
            duration_estimate TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id),
            business_name TEXT NOT NULL,
            owner_name TEXT,
            city TEXT,
            industry TEXT,
            phone TEXT,
            email TEXT,
            start_date TEXT,
            status TEXT DEFAULT 'active',
            monthly_value REAL DEFAULT 0,
            total_contract_value REAL DEFAULT 0,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            amount REAL NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'unpaid',
            due_date TEXT,
            paid_date TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS deliverables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER REFERENCES clients(id),
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            due_date TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id),
            type TEXT,
            message_draft TEXT,
            scheduled_for TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS call_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            industry TEXT,
            opener_type TEXT,
            cta_type TEXT,
            outcome TEXT,
            city TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
