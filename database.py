"""
School Management Database
- Creates SQLite tables (schema)
- Inserts large dummy data for testing queries & dashboards
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "school.db"

# ---- Dummy data sizes (large enough to verify dashboards) ----
N_TEACHERS = 80
N_CLASSES = 40
N_STUDENTS = 2500
N_ATTENDANCE_DAYS = 60  # last 60 school days (approx)
N_FEES_PER_STUDENT = 3  # fee records per student


FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharv", "Advaith", "Pranav", "Rudra",
    "Ananya", "Aadhya", "Diya", "Pari", "Anika", "Navya", "Myra", "Sara",
    "Ira", "Aisha", "Kiara", "Riya", "Saanvi", "Meera", "Kavya", "Neha",
    "Rohan", "Karan", "Nikhil", "Rahul", "Amit", "Suresh", "Priya", "Pooja",
    "Sneha", "Deepak", "Manish", "Vikram", "Nisha", "Tanvi", "Harsh", "Yash",
]

LAST_NAMES = [
    "Sharma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair", "Iyer",
    "Joshi", "Mehta", "Chopra", "Malhotra", "Verma", "Agarwal", "Shah",
    "Rao", "Pillai", "Desai", "Bhat", "Khan", "Das", "Banerjee", "Mukherjee",
]

SUBJECTS = [
    "Mathematics", "Science", "English", "History", "Geography",
    "Physics", "Chemistry", "Biology", "Computer Science", "Economics",
    "Art", "Physical Education", "Hindi", "Music",
]

CLASS_NAMES = [
    f"Grade {g}-{sec}" for g in range(1, 11) for sec in list("ABCD")
]

FEE_TYPES = ["Tuition", "Lab", "Transport", "Library", "Sports"]
STATUSES = ["Present", "Absent", "Late"]


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and relationships."""
    conn.executescript(
        """
        DROP TABLE IF EXISTS fees;
        DROP TABLE IF EXISTS attendance;
        DROP TABLE IF EXISTS students;
        DROP TABLE IF EXISTS classes;
        DROP TABLE IF EXISTS teachers;

        CREATE TABLE teachers (
            teacher_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name    TEXT NOT NULL,
            subject      TEXT NOT NULL,
            email        TEXT UNIQUE NOT NULL,
            phone        TEXT,
            hire_date    TEXT NOT NULL,
            salary       REAL NOT NULL
        );

        CREATE TABLE classes (
            class_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name   TEXT UNIQUE NOT NULL,
            grade_level  INTEGER NOT NULL,
            room_number  TEXT,
            teacher_id   INTEGER,
            capacity     INTEGER NOT NULL DEFAULT 40,
            FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
        );

        CREATE TABLE students (
            student_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name    TEXT NOT NULL,
            gender       TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            email        TEXT,
            phone        TEXT,
            class_id     INTEGER,
            enrollment_date TEXT NOT NULL,
            status       TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (class_id) REFERENCES classes(class_id)
        );

        CREATE TABLE attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            class_id      INTEGER NOT NULL,
            attend_date   TEXT NOT NULL,
            status        TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (class_id) REFERENCES classes(class_id)
        );

        CREATE TABLE fees (
            fee_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            fee_type      TEXT NOT NULL,
            amount        REAL NOT NULL,
            due_date      TEXT NOT NULL,
            paid_date     TEXT,
            payment_status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        );

        CREATE INDEX idx_students_class ON students(class_id);
        CREATE INDEX idx_attendance_date ON attendance(attend_date);
        CREATE INDEX idx_attendance_student ON attendance(student_id);
        CREATE INDEX idx_fees_student ON fees(student_id);
        CREATE INDEX idx_fees_status ON fees(payment_status);
        """
    )
    conn.commit()


def _rand_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def _rand_phone() -> str:
    return f"+91-{random.randint(7000000000, 9999999999)}"


def _rand_email(name: str, i: int) -> str:
    slug = name.lower().replace(" ", ".")
    return f"{slug}.{i}@school.edu"


def seed_huge_data(conn: sqlite3.Connection, seed: int = 42) -> dict:
    """Insert large dummy dataset. Returns row counts."""
    random.seed(seed)
    cur = conn.cursor()

    # ---- Teachers ----
    teachers = []
    start_hire = date(2015, 1, 1)
    for i in range(N_TEACHERS):
        name = _rand_name()
        hire = start_hire + timedelta(days=random.randint(0, 3500))
        teachers.append(
            (
                name,
                random.choice(SUBJECTS),
                _rand_email(name, i + 1),
                _rand_phone(),
                hire.isoformat(),
                round(random.uniform(35000, 95000), 2),
            )
        )
    cur.executemany(
        """
        INSERT INTO teachers (full_name, subject, email, phone, hire_date, salary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        teachers,
    )

    teacher_ids = [r[0] for r in cur.execute("SELECT teacher_id FROM teachers").fetchall()]

    # ---- Classes ----
    class_rows = []
    for i, cname in enumerate(CLASS_NAMES[:N_CLASSES]):
        grade = int(cname.split()[1].split("-")[0])
        class_rows.append(
            (
                cname,
                grade,
                f"R{100 + i}",
                teacher_ids[i % len(teacher_ids)],
                random.randint(30, 45),
            )
        )
    cur.executemany(
        """
        INSERT INTO classes (class_name, grade_level, room_number, teacher_id, capacity)
        VALUES (?, ?, ?, ?, ?)
        """,
        class_rows,
    )

    class_ids = [r[0] for r in cur.execute("SELECT class_id FROM classes").fetchall()]

    # ---- Students ----
    students = []
    enroll_start = date(2022, 4, 1)
    for i in range(N_STUDENTS):
        name = _rand_name()
        gender = random.choice(["Male", "Female"])
        dob = date(2008, 1, 1) + timedelta(days=random.randint(0, 4000))
        enroll = enroll_start + timedelta(days=random.randint(0, 900))
        students.append(
            (
                name,
                gender,
                dob.isoformat(),
                _rand_email(name, 1000 + i),
                _rand_phone(),
                random.choice(class_ids),
                enroll.isoformat(),
                random.choices(["Active", "Inactive"], weights=[92, 8])[0],
            )
        )
    cur.executemany(
        """
        INSERT INTO students
        (full_name, gender, date_of_birth, email, phone, class_id, enrollment_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        students,
    )

    student_rows = cur.execute(
        "SELECT student_id, class_id FROM students WHERE status = 'Active'"
    ).fetchall()

    # ---- Attendance (sample subset of students × days to keep DB usable but large) ----
    # ~800 active students × 60 days ≈ 48k rows
    sample_students = student_rows[:800]
    today = date.today()
    attendance_rows = []
    for day_offset in range(N_ATTENDANCE_DAYS):
        d = today - timedelta(days=day_offset)
        if d.weekday() >= 5:  # skip weekends
            continue
        for sid, cid in sample_students:
            status = random.choices(STATUSES, weights=[85, 10, 5])[0]
            attendance_rows.append((sid, cid, d.isoformat(), status))

    cur.executemany(
        """
        INSERT INTO attendance (student_id, class_id, attend_date, status)
        VALUES (?, ?, ?, ?)
        """,
        attendance_rows,
    )

    # ---- Fees ----
    all_students = cur.execute("SELECT student_id FROM students").fetchall()
    fee_rows = []
    for (sid,) in all_students:
        for _ in range(N_FEES_PER_STUDENT):
            fee_type = random.choice(FEE_TYPES)
            amount = round(random.uniform(500, 15000), 2)
            due = date(2025, 1, 1) + timedelta(days=random.randint(0, 500))
            paid = random.random() < 0.72
            paid_date = (due + timedelta(days=random.randint(-5, 20))).isoformat() if paid else None
            status = "Paid" if paid else random.choice(["Pending", "Overdue"])
            fee_rows.append(
                (sid, fee_type, amount, due.isoformat(), paid_date, status)
            )

    cur.executemany(
        """
        INSERT INTO fees
        (student_id, fee_type, amount, due_date, paid_date, payment_status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        fee_rows,
    )

    conn.commit()

    counts = {
        "teachers": cur.execute("SELECT COUNT(*) FROM teachers").fetchone()[0],
        "classes": cur.execute("SELECT COUNT(*) FROM classes").fetchone()[0],
        "students": cur.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "attendance": cur.execute("SELECT COUNT(*) FROM attendance").fetchone()[0],
        "fees": cur.execute("SELECT COUNT(*) FROM fees").fetchone()[0],
    }
    return counts


def init_database(force_reset: bool = False) -> dict:
    """
    Create DB + seed if missing, or force rebuild.
    Returns table row counts.
    """
    needs_seed = force_reset or not DB_PATH.exists()
    conn = get_connection()
    try:
        if needs_seed:
            create_schema(conn)
            counts = seed_huge_data(conn)
        else:
            cur = conn.cursor()
            counts = {
                "teachers": cur.execute("SELECT COUNT(*) FROM teachers").fetchone()[0],
                "classes": cur.execute("SELECT COUNT(*) FROM classes").fetchone()[0],
                "students": cur.execute("SELECT COUNT(*) FROM students").fetchone()[0],
                "attendance": cur.execute("SELECT COUNT(*) FROM attendance").fetchone()[0],
                "fees": cur.execute("SELECT COUNT(*) FROM fees").fetchone()[0],
            }
        return counts
    finally:
        conn.close()


def run_query(sql: str):
    """Execute a read/write SQL and return (columns, rows) or raise."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        if sql.strip().lower().startswith(("select", "with", "pragma", "explain")):
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return cols, [tuple(r) for r in rows]
        conn.commit()
        return ["message"], [(f"OK — {cur.rowcount} row(s) affected",)]
    finally:
        conn.close()


def get_schema_info() -> dict:
    """Return tables, columns, and foreign-key relationships for flow diagram."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        tables = [
            r[0]
            for r in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        columns = {}
        for t in tables:
            columns[t] = [
                {"name": r[1], "type": r[2], "pk": bool(r[5])}
                for r in cur.execute(f"PRAGMA table_info({t})").fetchall()
            ]
        edges = []
        for t in tables:
            for fk in cur.execute(f"PRAGMA foreign_key_list({t})").fetchall():
                # fk: id, seq, table, from, to, on_update, on_delete, match
                edges.append(
                    {
                        "from_table": t,
                        "from_col": fk[3],
                        "to_table": fk[2],
                        "to_col": fk[4],
                    }
                )
        return {"tables": tables, "columns": columns, "edges": edges}
    finally:
        conn.close()


if __name__ == "__main__":
    print("Building school.db with huge dummy data...")
    counts = init_database(force_reset=True)
    print("Done. Row counts:")
    for k, v in counts.items():
        print(f"  {k}: {v:,}")
