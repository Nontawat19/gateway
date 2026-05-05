import sqlite3
import os
from datetime import datetime
import json

DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            school_id TEXT,
            user_id TEXT NOT NULL,
            user_type TEXT NOT NULL,
            action_type TEXT NOT NULL, -- 'in' or 'out'
            status TEXT NOT NULL,
            scan_date TEXT NOT NULL, -- YYYY-MM-DD
            scan_time TEXT NOT NULL, -- HH:mm:ss
            is_synced INTEGER DEFAULT 0, -- 0=No, 1=Yes
            last_notified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users_cache (
            user_id TEXT PRIMARY KEY,
            school_id TEXT,
            user_data TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_cached_user(user_id):
    """ดึงข้อมูลผู้ใช้จาก SQLite (ถ้ามี)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_data FROM users_cache WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return json.loads(row[0])
    return None

def update_user_cache(user_id, school_id, user_data):
    """บันทึก/อัปเดตข้อมูลผู้ใช้ลงใน SQLite"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users_cache (user_id, school_id, user_data, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, school_id, json.dumps(user_data)))
    conn.commit()
    conn.close()

def check_existing_record(user_id, scan_date, action_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM local_attendance 
        WHERE user_id = ? AND scan_date = ? AND action_type = ?
    """, (user_id, scan_date, action_type))
    record = cursor.fetchone()
    conn.close()
    return record is not None

def insert_record(school_id, user_id, user_type, action_type, status, scan_date, scan_time):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO local_attendance (school_id, user_id, user_type, action_type, status, scan_date, scan_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (school_id, user_id, user_type, action_type, status, scan_date, scan_time))
    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id

def update_sync_status(record_id, status=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE local_attendance SET is_synced = ? WHERE id = ?", (status, record_id))
    conn.commit()
    conn.close()

def get_unsynced_records():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM local_attendance WHERE is_synced = 0")
    records = cursor.fetchall()
    conn.close()
    return records

def clear_old_records(before_date):
    """ลบข้อมูลที่เก่ากว่าวันที่กำหนด (เพื่อล้างข้อมูลข้ามวัน)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # ลบข้อมูลที่เก่ากว่าวันที่กำหนด และส่งขึ้น Firebase สำเร็จแล้ว (is_synced=1)
    # หรือจะลบทั้งหมดที่เก่ากว่าวันนี้เลยก็ได้ตามต้องการ
    cursor.execute("DELETE FROM local_attendance WHERE scan_date < ?", (before_date,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count
