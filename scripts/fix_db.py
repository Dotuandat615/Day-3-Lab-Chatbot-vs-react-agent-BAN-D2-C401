"""Fix time values in appointment_slots."""
import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "hospital.db")

conn = sqlite3.connect(DB)

# Populate time from start_time
conn.execute("UPDATE appointment_slots SET time = start_time WHERE start_time IS NOT NULL")
conn.commit()
print("Copied start_time -> time")

# Fix empty estimated_wait_time
conn.execute("UPDATE appointment_slots SET estimated_wait_time = 30 WHERE estimated_wait_time IS NULL OR CAST(estimated_wait_time AS TEXT) = ''")
conn.commit()
print("Fixed null estimated_wait_time -> 30")

# Check
null_time = conn.execute("SELECT COUNT(*) FROM appointment_slots WHERE time IS NULL").fetchone()[0]
avail = conn.execute("SELECT COUNT(*) FROM appointment_slots WHERE available=1 AND time IS NOT NULL").fetchone()[0]
print(f"Slots with time=NULL: {null_time}")
print(f"Available slots with valid time: {avail}")

# Verify sample
rows = conn.execute("""
    SELECT s.slot_id, d.doctor_name, s.date, s.time, s.estimated_wait_time, sp.specialty_name
    FROM appointment_slots s
    JOIN doctors d ON s.doctor_id = d.doctor_id
    JOIN specialties sp ON d.specialty_id = sp.specialty_id
    WHERE s.available = 1 AND s.date >= '2026-06-02' AND s.time IS NOT NULL
    ORDER BY s.date, s.time
    LIMIT 8
""").fetchall()
conn.row_factory = sqlite3.Row
print("\nSample working slots:")
for r in rows:
    print(f"  {r[0]} | {r[1]} | {r[2]} {r[3]} | wait={r[4]} | {r[5]}")

conn.close()
print("\nDatabase fix complete!")
