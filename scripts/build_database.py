"""
scripts/build_database.py
=========================
Chuyển đổi toàn bộ CSV trong data/ thành SQLite database data/hospital.db.
Chạy một lần trước khi khởi động app:
    python scripts/build_database.py

Schema được tạo ra phù hợp với appointment_tools.py (Người 3).
"""

import os
import csv
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH  = os.path.join(DATA_DIR, "hospital.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS hospital_info (
    hospital_id   TEXT PRIMARY KEY,
    hospital_name TEXT,
    address       TEXT,
    city          TEXT,
    opening_time  TEXT,
    closing_time  TEXT,
    weekend_available TEXT,
    parking_available TEXT,
    hotline       TEXT,
    emergency_note TEXT
);

CREATE TABLE IF NOT EXISTS specialties (
    specialty_id   TEXT PRIMARY KEY,
    specialty_name TEXT NOT NULL,
    description    TEXT,
    common_symptoms TEXT,
    min_age        INTEGER,
    max_age        INTEGER
);

CREATE TABLE IF NOT EXISTS symptom_specialty_map (
    symptom_id          TEXT PRIMARY KEY,
    symptom_keyword     TEXT,
    suggested_specialty_id TEXT,
    urgency_level       TEXT,
    note                TEXT
);

CREATE TABLE IF NOT EXISTS payment_coverage_types (
    coverage_type_id TEXT PRIMARY KEY,
    coverage_name    TEXT,
    description      TEXT
);

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id       TEXT PRIMARY KEY,
    doctor_name     TEXT NOT NULL,
    gender          TEXT,
    specialty_id    TEXT,
    room            TEXT,
    experience_years INTEGER,
    languages       TEXT,
    rating          REAL,
    consultation_fee INTEGER,
    bhyt_supported  TEXT,
    private_insurance_supported TEXT,
    telehealth_supported TEXT,
    FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id)
);

CREATE TABLE IF NOT EXISTS services (
    service_id      TEXT PRIMARY KEY,
    specialty_id    TEXT,
    service_name    TEXT,
    duration_minutes INTEGER,
    base_price      INTEGER,
    preparation_required TEXT,
    preparation_note TEXT,
    bhyt_supported  TEXT,
    private_insurance_supported TEXT,
    self_pay_available TEXT,
    estimated_bhyt_price_note TEXT,
    estimated_private_price_note TEXT,
    FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id)
);

CREATE TABLE IF NOT EXISTS doctor_schedule_templates (
    schedule_id  TEXT PRIMARY KEY,
    doctor_id    TEXT,
    day_of_week  TEXT,
    shift        TEXT,
    start_time   TEXT,
    end_time     TEXT,
    max_patients INTEGER,
    is_active    TEXT,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);

CREATE TABLE IF NOT EXISTS appointment_slots (
    slot_id             TEXT PRIMARY KEY,
    doctor_id           TEXT,
    service_id          TEXT,
    date                TEXT NOT NULL,
    time                TEXT,
    start_time          TEXT,
    end_time            TEXT,
    status              TEXT,
    capacity            INTEGER,
    booked_count        INTEGER,
    estimated_wait_time INTEGER,
    is_telehealth       TEXT,
    room                TEXT,
    available           INTEGER DEFAULT 1,
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);

CREATE TABLE IF NOT EXISTS wait_time_history (
    history_id     TEXT PRIMARY KEY,
    specialty_id   TEXT,
    day_of_week    TEXT,
    hour_block     INTEGER,
    avg_wait_time  REAL,
    no_show_rate   REAL,
    patient_volume INTEGER
);

CREATE TABLE IF NOT EXISTS patients (
    patient_id           TEXT PRIMARY KEY,
    patient_name         TEXT,
    phone                TEXT,
    date_of_birth        TEXT,
    gender               TEXT,
    coverage_type_id     TEXT,
    private_insurance_name TEXT,
    preferred_language   TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id TEXT PRIMARY KEY,
    patient_id     TEXT,
    slot_id        TEXT,
    reason_for_visit TEXT,
    status         TEXT,
    created_at     TEXT,
    reminder_sent  TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (slot_id)    REFERENCES appointment_slots(slot_id)
);

CREATE TABLE IF NOT EXISTS reminder_logs (
    reminder_id    TEXT PRIMARY KEY,
    appointment_id TEXT,
    channel        TEXT,
    sent_at        TEXT,
    delivery_status TEXT,
    message_type   TEXT
);

CREATE TABLE IF NOT EXISTS hospital_policies (
    policy_id   TEXT PRIMARY KEY,
    category    TEXT,
    question    TEXT,
    answer      TEXT,
    applies_to  TEXT
);

CREATE TABLE IF NOT EXISTS escalation_tickets (
    ticket_id   TEXT PRIMARY KEY,
    user_query  TEXT,
    reason      TEXT,
    status      TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS feedback_reviews (
    review_id      TEXT PRIMARY KEY,
    appointment_id TEXT,
    rating         INTEGER,
    wait_satisfaction INTEGER,
    comment        TEXT,
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS data_dictionary (
    table_name   TEXT,
    description  TEXT
);
"""

# ---------------------------------------------------------------------------
# Mapping: CSV filename -> table name
# ---------------------------------------------------------------------------
CSV_TABLE_MAP = {
    "hospital_info.csv":              "hospital_info",
    "specialties.csv":                "specialties",
    "symptom_specialty_map.csv":      "symptom_specialty_map",
    "payment_coverage_types.csv":     "payment_coverage_types",
    "doctors.csv":                    "doctors",
    "services.csv":                   "services",
    "doctor_schedule_templates.csv":  "doctor_schedule_templates",
    "appointment_slots.csv":          "appointment_slots",
    "wait_time_history.csv":          "wait_time_history",
    "patients.csv":                   "patients",
    "appointments.csv":               "appointments",
    "reminder_logs.csv":              "reminder_logs",
    "hospital_policies.csv":          "hospital_policies",
    "escalation_tickets.csv":         "escalation_tickets",
    "feedback_reviews.csv":           "feedback_reviews",
    "data_dictionary.csv":            "data_dictionary",
}


def _load_csv(path: str) -> list[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Làm sạch key (xóa khoảng trắng đầu/cuối)
            rows.append({k.strip(): (v.strip() if v else v) for k, v in row.items()})
    return rows


def _insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_list}) VALUES ({placeholders})"
    data = [[row.get(c, None) for c in cols] for row in rows]
    conn.executemany(sql, data)
    return len(data)


def _compute_available(conn: sqlite3.Connection):
    """
    Tính lại cột `available` trong appointment_slots dựa trên status và booked_count/capacity.
    - available=1 nếu status = 'available' hoặc booked_count < capacity
    - available=0 ngược lại
    """
    conn.execute("""
        UPDATE appointment_slots
        SET available = CASE
            WHEN LOWER(TRIM(status)) IN ('available', 'open') THEN 1
            WHEN booked_count IS NOT NULL AND capacity IS NOT NULL AND CAST(booked_count AS INTEGER) < CAST(capacity AS INTEGER) THEN 1
            ELSE 0
        END
    """)


def build():
    print(f"Building database: {DB_PATH}")
    print(f"Data directory:    {DATA_DIR}")
    print()

    conn = _connect()

    # Drop & recreate
    print("Creating tables...")
    conn.executescript(DDL)
    conn.commit()

    total_rows = 0
    for csv_file, table_name in CSV_TABLE_MAP.items():
        csv_path = os.path.join(DATA_DIR, csv_file)
        if not os.path.exists(csv_path):
            print(f"  SKIP (not found): {csv_file}")
            continue
        try:
            rows = _load_csv(csv_path)
            n = _insert_rows(conn, table_name, rows)
            conn.commit()
            total_rows += n
            print(f"  OK  {csv_file:<45} -> {table_name:<35} ({n} rows)")
        except Exception as e:
            print(f"  FAIL {csv_file}: {e}")
            conn.rollback()

    # Post-process: tính cột `available`
    print("\nPost-processing appointment_slots.available ...")
    try:
        _compute_available(conn)
        conn.commit()
        avail_count = conn.execute("SELECT COUNT(*) FROM appointment_slots WHERE available=1").fetchone()[0]
        total_slots = conn.execute("SELECT COUNT(*) FROM appointment_slots").fetchone()[0]
        print(f"  Slots: {avail_count}/{total_slots} available")
    except Exception as e:
        print(f"  Warning: {e}")

    # Summary
    print(f"\nTotal rows inserted: {total_rows}")
    db_size = os.path.getsize(DB_PATH) / 1024
    print(f"Database size: {db_size:.1f} KB")

    # Quick verification
    print("\n--- Quick verification ---")
    for table in ["specialties", "doctors", "appointment_slots", "hospital_policies"]:
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count} rows")
        except Exception as e:
            print(f"  {table}: ERROR - {e}")

    conn.close()
    print(f"\nDone! Database ready at: {DB_PATH}")
    return DB_PATH


if __name__ == "__main__":
    build()
