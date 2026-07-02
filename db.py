"""Database helpers for MySQL."""

from contextlib import contextmanager
from datetime import date, datetime

import pymysql
import pymysql.cursors
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    SQL_SCHEMA_PATH,
    UNIVERSITY_EMAIL_DOMAIN,
)


def _mysql_config(database=None):
    config = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }
    if database:
        config["database"] = database
    return config


def get_connection(database=MYSQL_DATABASE):
    return pymysql.connect(**_mysql_config(database))


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _normalize_row(row):
    if row is None:
        return None
    result = dict(row)
    for key, value in result.items():
        if isinstance(value, datetime):
            result[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, date):
            result[key] = value.isoformat()
    return result


def _normalize_rows(rows):
    return [_normalize_row(row) for row in rows]


def _execute(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    return cursor


def _fetchone(cursor, sql, params=None):
    _execute(cursor, sql, params)
    return _normalize_row(cursor.fetchone())


def _fetchall(cursor, sql, params=None):
    _execute(cursor, sql, params)
    return _normalize_rows(cursor.fetchall())


def _table_exists(cursor, table_name):
    row = _fetchone(
        cursor,
        "SELECT COUNT(*) AS count FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (MYSQL_DATABASE, table_name),
    )
    return row["count"] > 0


def _column_exists(cursor, table_name, column_name):
    row = _fetchone(
        cursor,
        "SELECT COUNT(*) AS count FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = %s",
        (MYSQL_DATABASE, table_name, column_name),
    )
    return row["count"] > 0


def _run_schema(cursor, schema_sql):
    """Execute SQL schema statements from the schema file."""
    statement_lines = []

    for line in schema_sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        statement_lines.append(line)
        if stripped.endswith(";"):
            sql = "\n".join(statement_lines).strip()
            if sql:
                cursor.execute(sql)
            statement_lines = []


def _migrate_schema(cursor):
    """Apply incremental schema changes for existing installations."""
    _execute(
        cursor,
        "ALTER TABLE users MODIFY role ENUM('student', 'admin', 'lecturer') "
        "NOT NULL DEFAULT 'student'",
    )

    if not _table_exists(cursor, "lecturer_profiles"):
        _execute(
            cursor,
            """CREATE TABLE lecturer_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                employee_id VARCHAR(50) UNIQUE,
                department VARCHAR(120),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )""",
        )

    if not _table_exists(cursor, "classes"):
        _execute(
            cursor,
            """CREATE TABLE classes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                department VARCHAR(120),
                academic_year VARCHAR(20),
                semester VARCHAR(20),
                lecturer_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lecturer_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_classes_lecturer (lecturer_id)
            )""",
        )

    if not _table_exists(cursor, "courses"):
        _execute(
            cursor,
            """CREATE TABLE courses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class_id INT NOT NULL,
                name VARCHAR(120) NOT NULL,
                code VARCHAR(50) NOT NULL,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                UNIQUE KEY uq_course_class_code (class_id, code),
                INDEX idx_courses_class (class_id)
            )""",
        )

    if not _table_exists(cursor, "class_enrollments"):
        _execute(
            cursor,
            """CREATE TABLE class_enrollments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class_id INT NOT NULL,
                student_user_id INT NOT NULL,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY uq_class_student (class_id, student_user_id),
                INDEX idx_enrollments_student (student_user_id)
            )""",
        )

    if not _table_exists(cursor, "marks"):
        _execute(
            cursor,
            """CREATE TABLE marks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT NOT NULL,
                student_user_id INT NOT NULL,
                title VARCHAR(120) NOT NULL,
                mark_type ENUM('assignment', 'exam', 'quiz') NOT NULL DEFAULT 'assignment',
                score DOUBLE NOT NULL,
                max_score DOUBLE NOT NULL DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_marks_student (student_user_id),
                INDEX idx_marks_course (course_id)
            )""",
        )

    if not _table_exists(cursor, "attendance_sessions"):
        _execute(
            cursor,
            """CREATE TABLE attendance_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class_id INT NOT NULL,
                session_date DATE NOT NULL,
                note VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                INDEX idx_attendance_class (class_id)
            )""",
        )

    if not _table_exists(cursor, "attendance_records"):
        _execute(
            cursor,
            """CREATE TABLE attendance_records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                student_user_id INT NOT NULL,
                status ENUM('present', 'absent') NOT NULL DEFAULT 'present',
                FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY uq_session_student (session_id, student_user_id),
                INDEX idx_attendance_student (student_user_id)
            )""",
        )

    if _table_exists(cursor, "predictions"):
        if not _column_exists(cursor, "predictions", "class_id"):
            _execute(cursor, "ALTER TABLE predictions ADD COLUMN class_id INT NULL")
        if not _column_exists(cursor, "predictions", "course_id"):
            _execute(cursor, "ALTER TABLE predictions ADD COLUMN course_id INT NULL")
        if not _column_exists(cursor, "predictions", "created_by_id"):
            _execute(cursor, "ALTER TABLE predictions ADD COLUMN created_by_id INT NULL")

    if not _table_exists(cursor, "assignments"):
        _execute(
            cursor,
            """CREATE TABLE assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                course_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                deadline DATETIME NOT NULL,
                max_score DOUBLE NOT NULL DEFAULT 100,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
                INDEX idx_assignments_course (course_id),
                INDEX idx_assignments_deadline (deadline)
            )""",
        )

    if not _table_exists(cursor, "assignment_submissions"):
        _execute(
            cursor,
            """CREATE TABLE assignment_submissions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                assignment_id INT NOT NULL,
                student_user_id INT NOT NULL,
                answer TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score DOUBLE,
                feedback TEXT,
                graded_at TIMESTAMP NULL,
                mark_id INT NULL,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (mark_id) REFERENCES marks(id) ON DELETE SET NULL,
                UNIQUE KEY uq_assignment_student (assignment_id, student_user_id),
                INDEX idx_submissions_student (student_user_id)
            )""",
        )


def init_db():
    """Initialize MySQL database from schema file and ensure admin exists."""
    with open(SQL_SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = f.read()

    bootstrap_conn = get_connection(database=None)
    try:
        with bootstrap_conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        bootstrap_conn.commit()
    finally:
        bootstrap_conn.close()

    with get_db() as conn:
        with conn.cursor() as cursor:
            _run_schema(cursor, schema)
            _migrate_schema(cursor)

            admin = _fetchone(
                cursor,
                "SELECT id FROM users WHERE username = %s AND role = 'admin'",
                (ADMIN_USERNAME,),
            )

            if admin is None:
                _execute(
                    cursor,
                    """INSERT INTO users (username, email, password_hash, role, full_name)
                       VALUES (%s, %s, %s, 'admin', 'System Administrator')""",
                    (
                        ADMIN_USERNAME,
                        f"admin@{UNIVERSITY_EMAIL_DOMAIN}",
                        generate_password_hash(ADMIN_PASSWORD),
                    ),
                )


def _next_sequential_id(cursor, prefix, year, table, column):
    """Generate the next ID like MKU-2026-001 or EMP-2026-001."""
    pattern = f"{prefix}-{year}-%"
    row = _fetchone(
        cursor,
        f"""SELECT {column} FROM {table}
            WHERE {column} LIKE %s
            ORDER BY {column} DESC LIMIT 1""",
        (pattern,),
    )
    if row and row[column]:
        try:
            last_num = int(str(row[column]).rsplit("-", 1)[-1])
        except ValueError:
            last_num = 0
        next_num = last_num + 1
    else:
        next_num = 1
    return f"{prefix}-{year}-{next_num:03d}"


def generate_student_id(cursor):
    """Generate the next MKU student ID for the current year."""
    return _next_sequential_id(
        cursor, "MKU", datetime.now().year, "student_profiles", "student_id"
    )


def generate_employee_id(cursor):
    """Generate the next employee ID for the current year."""
    return _next_sequential_id(
        cursor, "EMP", datetime.now().year, "lecturer_profiles", "employee_id"
    )


def generate_class_code(cursor):
    """Generate the next class code for the current year."""
    return _next_sequential_id(cursor, "CLS", datetime.now().year, "classes", "code")


def create_student(username, email, password, full_name, department, year_of_study):
    """Register a new student account. Student ID is auto-generated."""
    password_hash = generate_password_hash(password)

    with get_db() as conn:
        with conn.cursor() as cursor:
            student_id = generate_student_id(cursor)
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role, full_name)
                   VALUES (%s, %s, %s, 'student', %s)""",
                (username, email, password_hash, full_name),
            )
            user_id = cursor.lastrowid

            cursor.execute(
                """INSERT INTO student_profiles (user_id, student_id, department, year_of_study)
                   VALUES (%s, %s, %s, %s)""",
                (user_id, student_id, department, year_of_study),
            )
            return user_id, student_id


def create_lecturer(username, email, password, full_name, department):
    """Create a lecturer account (admin only). Employee ID is auto-generated."""
    password_hash = generate_password_hash(password)

    with get_db() as conn:
        with conn.cursor() as cursor:
            employee_id = generate_employee_id(cursor)
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role, full_name)
                   VALUES (%s, %s, %s, 'lecturer', %s)""",
                (username, email, password_hash, full_name),
            )
            user_id = cursor.lastrowid

            cursor.execute(
                """INSERT INTO lecturer_profiles (user_id, employee_id, department)
                   VALUES (%s, %s, %s)""",
                (user_id, employee_id, department),
            )
            return user_id, employee_id


def authenticate_user(username, password):
    """Validate credentials and return user dict or None."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            user = _fetchone(cursor, "SELECT * FROM users WHERE username = %s", (username,))

    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def get_user_by_id(user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(cursor, "SELECT * FROM users WHERE id = %s", (user_id,))


def get_student_profile(user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor, "SELECT * FROM student_profiles WHERE user_id = %s", (user_id,)
            )


def get_lecturer_profile(user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor, "SELECT * FROM lecturer_profiles WHERE user_id = %s", (user_id,)
            )


def save_prediction(user_id, inputs, result, confidence, class_id=None, course_id=None, created_by_id=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO predictions
                   (user_id, class_id, course_id, created_by_id,
                    study_hours, attendance_rate, previous_gpa,
                    assignments_completed, extracurricular_hours, sleep_hours,
                    predicted_result, confidence_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    user_id,
                    class_id,
                    course_id,
                    created_by_id,
                    inputs["study_hours"],
                    inputs["attendance_rate"],
                    inputs["previous_gpa"],
                    inputs["assignments_completed"],
                    inputs["extracurricular_hours"],
                    inputs["sleep_hours"],
                    result,
                    confidence,
                ),
            )


def get_student_predictions(user_id, class_id=None, course_id=None, limit=20):
    with get_db() as conn:
        with conn.cursor() as cursor:
            sql = """SELECT p.*, c.name AS class_name, c.code AS class_code,
                            co.name AS course_name, co.code AS course_code
                     FROM predictions p
                     LEFT JOIN classes c ON p.class_id = c.id
                     LEFT JOIN courses co ON p.course_id = co.id
                     WHERE p.user_id = %s"""
            params = [user_id]

            if class_id:
                sql += " AND p.class_id = %s"
                params.append(class_id)
            if course_id:
                sql += " AND p.course_id = %s"
                params.append(course_id)

            sql += " ORDER BY p.created_at DESC LIMIT %s"
            params.append(limit)
            return _fetchall(cursor, sql, params)


def get_all_students():
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT u.id, u.username, u.email, u.full_name, u.created_at,
                          sp.student_id, sp.department, sp.year_of_study
                   FROM users u
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE u.role = 'student'
                   ORDER BY u.created_at DESC""",
            )


def get_all_lecturers():
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT u.id, u.username, u.email, u.full_name, u.created_at,
                          lp.employee_id, lp.department
                   FROM users u
                   LEFT JOIN lecturer_profiles lp ON u.id = lp.user_id
                   WHERE u.role = 'lecturer'
                   ORDER BY u.created_at DESC""",
            )


def get_all_predictions(limit=50):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT p.*, u.username, u.full_name,
                          c.name AS class_name, co.name AS course_name
                   FROM predictions p
                   JOIN users u ON p.user_id = u.id
                   LEFT JOIN classes c ON p.class_id = c.id
                   LEFT JOIN courses co ON p.course_id = co.id
                   ORDER BY p.created_at DESC LIMIT %s""",
                (limit,),
            )


def get_admin_stats():
    with get_db() as conn:
        with conn.cursor() as cursor:
            student_count = _fetchone(
                cursor, "SELECT COUNT(*) AS count FROM users WHERE role = 'student'"
            )["count"]
            lecturer_count = _fetchone(
                cursor, "SELECT COUNT(*) AS count FROM users WHERE role = 'lecturer'"
            )["count"]
            class_count = _fetchone(
                cursor, "SELECT COUNT(*) AS count FROM classes"
            )["count"]
            prediction_count = _fetchone(
                cursor, "SELECT COUNT(*) AS count FROM predictions"
            )["count"]
            at_risk = _fetchone(
                cursor,
                "SELECT COUNT(*) AS count FROM predictions WHERE predicted_result = 'At Risk'",
            )["count"]
            high_performer = _fetchone(
                cursor,
                "SELECT COUNT(*) AS count FROM predictions WHERE predicted_result = 'High Performer'",
            )["count"]

    return {
        "student_count": student_count,
        "lecturer_count": lecturer_count,
        "class_count": class_count,
        "prediction_count": prediction_count,
        "at_risk_count": at_risk,
        "high_performer_count": high_performer,
    }


def username_exists(username):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(cursor, "SELECT id FROM users WHERE username = %s", (username,))
            return row is not None


def email_exists(email):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(cursor, "SELECT id FROM users WHERE email = %s", (email,))
            return row is not None


def employee_id_exists(employee_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(
                cursor, "SELECT id FROM lecturer_profiles WHERE employee_id = %s", (employee_id,)
            )
            return row is not None


def create_class(name, department, academic_year, semester, lecturer_id):
    """Create a class. Class code is auto-generated."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            code = generate_class_code(cursor)
            cursor.execute(
                """INSERT INTO classes (name, code, department, academic_year, semester, lecturer_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (name, code, department, academic_year, semester, lecturer_id),
            )
            return cursor.lastrowid, code


def get_all_classes():
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT c.*, u.full_name AS lecturer_name, u.username AS lecturer_username,
                          (SELECT COUNT(*) FROM class_enrollments ce WHERE ce.class_id = c.id) AS student_count
                   FROM classes c
                   JOIN users u ON c.lecturer_id = u.id
                   ORDER BY c.created_at DESC""",
            )


def get_class_by_id(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor,
                """SELECT c.*, u.full_name AS lecturer_name
                   FROM classes c
                   JOIN users u ON c.lecturer_id = u.id
                   WHERE c.id = %s""",
                (class_id,),
            )


def get_lecturer_classes(lecturer_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT c.*,
                          (SELECT COUNT(*) FROM class_enrollments ce WHERE ce.class_id = c.id) AS student_count
                   FROM classes c
                   WHERE c.lecturer_id = %s
                   ORDER BY c.name""",
                (lecturer_id,),
            )


def lecturer_owns_class(lecturer_id, class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(
                cursor,
                "SELECT id FROM classes WHERE id = %s AND lecturer_id = %s",
                (class_id, lecturer_id),
            )
            return row is not None


def create_course(class_id, name, code):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO courses (class_id, name, code) VALUES (%s, %s, %s)",
                (class_id, name, code),
            )
            return cursor.lastrowid


def get_courses_by_class(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                "SELECT * FROM courses WHERE class_id = %s ORDER BY name",
                (class_id,),
            )


def get_course_by_id(course_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(cursor, "SELECT * FROM courses WHERE id = %s", (course_id,))


def enroll_student_in_class(class_id, student_user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO class_enrollments (class_id, student_user_id) VALUES (%s, %s)",
                (class_id, student_user_id),
            )


def remove_student_from_class(class_id, student_user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM class_enrollments WHERE class_id = %s AND student_user_id = %s",
                (class_id, student_user_id),
            )


def get_class_students(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT u.id, u.username, u.full_name, u.email,
                          sp.student_id, sp.department, ce.enrolled_at
                   FROM class_enrollments ce
                   JOIN users u ON ce.student_user_id = u.id
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE ce.class_id = %s
                   ORDER BY u.full_name""",
                (class_id,),
            )


def get_unenrolled_students(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT u.id, u.username, u.full_name, sp.student_id, sp.department
                   FROM users u
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE u.role = 'student'
                     AND u.id NOT IN (
                         SELECT student_user_id FROM class_enrollments WHERE class_id = %s
                     )
                   ORDER BY u.full_name""",
                (class_id,),
            )


def get_student_classes(student_user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT c.*, u.full_name AS lecturer_name
                   FROM class_enrollments ce
                   JOIN classes c ON ce.class_id = c.id
                   JOIN users u ON c.lecturer_id = u.id
                   WHERE ce.student_user_id = %s
                   ORDER BY c.name""",
                (student_user_id,),
            )


def add_mark(course_id, student_user_id, title, mark_type, score, max_score):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO marks (course_id, student_user_id, title, mark_type, score, max_score)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (course_id, student_user_id, title, mark_type, score, max_score),
            )


def get_marks_for_class(class_id, student_user_id=None, course_id=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            sql = """SELECT m.*, co.name AS course_name, co.code AS course_code,
                            u.full_name AS student_name
                     FROM marks m
                     JOIN courses co ON m.course_id = co.id
                     JOIN users u ON m.student_user_id = u.id
                     WHERE co.class_id = %s"""
            params = [class_id]

            if student_user_id:
                sql += " AND m.student_user_id = %s"
                params.append(student_user_id)
            if course_id:
                sql += " AND m.course_id = %s"
                params.append(course_id)

            sql += " ORDER BY m.created_at DESC"
            return _fetchall(cursor, sql, params)


def create_attendance_session(class_id, session_date, note=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO attendance_sessions (class_id, session_date, note) VALUES (%s, %s, %s)",
                (class_id, session_date, note),
            )
            return cursor.lastrowid


def get_attendance_sessions(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT s.*,
                          (SELECT COUNT(*) FROM attendance_records ar
                           WHERE ar.session_id = s.id AND ar.status = 'present') AS present_count,
                          (SELECT COUNT(*) FROM attendance_records ar
                           WHERE ar.session_id = s.id AND ar.status = 'absent') AS absent_count
                   FROM attendance_sessions s
                   WHERE s.class_id = %s
                   ORDER BY s.session_date DESC""",
                (class_id,),
            )


def save_attendance_records(session_id, records):
    """records: list of (student_user_id, status) tuples."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            for student_user_id, status in records:
                cursor.execute(
                    """INSERT INTO attendance_records (session_id, student_user_id, status)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE status = VALUES(status)""",
                    (session_id, student_user_id, status),
                )


def get_attendance_for_session(session_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT ar.*, u.full_name, sp.student_id
                   FROM attendance_records ar
                   JOIN users u ON ar.student_user_id = u.id
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE ar.session_id = %s
                   ORDER BY u.full_name""",
                (session_id,),
            )


def get_student_attendance_rate(student_user_id, class_id):
    """Return attendance percentage for a student in a class."""
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(
                cursor,
                """SELECT
                       COUNT(*) AS total,
                       SUM(CASE WHEN ar.status = 'present' THEN 1 ELSE 0 END) AS present_count
                   FROM attendance_records ar
                   JOIN attendance_sessions s ON ar.session_id = s.id
                   WHERE ar.student_user_id = %s AND s.class_id = %s""",
                (student_user_id, class_id),
            )
            if not row or row["total"] == 0:
                return 75.0
            return round((row["present_count"] / row["total"]) * 100, 1)


def build_prediction_inputs(student_user_id, class_id, course_id=None):
    """Build ML feature inputs from stored marks and attendance."""
    attendance_rate = get_student_attendance_rate(student_user_id, class_id)

    marks = get_marks_for_class(class_id, student_user_id=student_user_id, course_id=course_id)

    if marks:
        gpa_scores = [(m["score"] / m["max_score"]) * 4.0 for m in marks if m["max_score"] > 0]
        previous_gpa = round(sum(gpa_scores) / len(gpa_scores), 2)
        assignments_completed = min(
            20, sum(1 for m in marks if m["mark_type"] == "assignment")
        )
    else:
        previous_gpa = 2.5
        assignments_completed = 10

    return {
        "study_hours": 5.0,
        "attendance_rate": attendance_rate,
        "previous_gpa": previous_gpa,
        "assignments_completed": assignments_completed,
        "extracurricular_hours": 3.0,
        "sleep_hours": 7.0,
    }


def get_class_predictions(class_id, course_id=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            sql = """SELECT p.*, u.full_name, u.username, sp.student_id,
                            co.name AS course_name
                     FROM predictions p
                     JOIN users u ON p.user_id = u.id
                     LEFT JOIN student_profiles sp ON u.id = sp.user_id
                     LEFT JOIN courses co ON p.course_id = co.id
                     WHERE p.class_id = %s"""
            params = [class_id]

            if course_id:
                sql += " AND p.course_id = %s"
                params.append(course_id)
            else:
                sql += " AND p.course_id IS NULL"

            sql += """ AND p.id IN (
                         SELECT MAX(p2.id) FROM predictions p2
                         WHERE p2.class_id = %s"""
            params.append(class_id)
            if course_id:
                sql += " AND p2.course_id = %s"
                params.append(course_id)
            else:
                sql += " AND p2.course_id IS NULL"
            sql += " GROUP BY p2.user_id) ORDER BY u.full_name"
            return _fetchall(cursor, sql, params)


def student_enrolled_in_class(student_user_id, class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(
                cursor,
                "SELECT id FROM class_enrollments WHERE class_id = %s AND student_user_id = %s",
                (class_id, student_user_id),
            )
            return row is not None


def get_assignment_class_id(assignment_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            row = _fetchone(
                cursor,
                """SELECT co.class_id FROM assignments a
                   JOIN courses co ON a.course_id = co.id
                   WHERE a.id = %s""",
                (assignment_id,),
            )
            return row["class_id"] if row else None


def create_assignment(course_id, title, description, deadline, max_score=100):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO assignments (course_id, title, description, deadline, max_score)
                   VALUES (%s, %s, %s, %s, %s)""",
                (course_id, title, description, deadline, max_score),
            )
            return cursor.lastrowid


def get_assignment_by_id(assignment_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor,
                """SELECT a.*, co.name AS course_name, co.code AS course_code,
                          co.class_id, c.name AS class_name, c.code AS class_code
                   FROM assignments a
                   JOIN courses co ON a.course_id = co.id
                   JOIN classes c ON co.class_id = c.id
                   WHERE a.id = %s""",
                (assignment_id,),
            )


def get_assignments_by_class(class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT a.*, co.name AS course_name, co.code AS course_code,
                          (SELECT COUNT(*) FROM assignment_submissions s
                           WHERE s.assignment_id = a.id) AS submission_count,
                          (SELECT COUNT(*) FROM assignment_submissions s
                           WHERE s.assignment_id = a.id AND s.score IS NOT NULL) AS graded_count
                   FROM assignments a
                   JOIN courses co ON a.course_id = co.id
                   WHERE co.class_id = %s
                   ORDER BY a.deadline DESC""",
                (class_id,),
            )


def get_assignments_for_student(student_user_id, class_id=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            sql = """SELECT a.*, co.name AS course_name, co.code AS course_code,
                            c.id AS class_id, c.name AS class_name, c.code AS class_code,
                            s.id AS submission_id, s.submitted_at, s.score, s.feedback
                     FROM assignments a
                     JOIN courses co ON a.course_id = co.id
                     JOIN classes c ON co.class_id = c.id
                     JOIN class_enrollments ce ON ce.class_id = c.id
                     LEFT JOIN assignment_submissions s
                       ON s.assignment_id = a.id AND s.student_user_id = %s
                     WHERE ce.student_user_id = %s"""
            params = [student_user_id, student_user_id]
            if class_id:
                sql += " AND c.id = %s"
                params.append(class_id)
            sql += " ORDER BY a.deadline ASC"
            return _fetchall(cursor, sql, params)


def get_submission_by_id(submission_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor, "SELECT * FROM assignment_submissions WHERE id = %s", (submission_id,)
            )


def get_submission(assignment_id, student_user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchone(
                cursor,
                """SELECT * FROM assignment_submissions
                   WHERE assignment_id = %s AND student_user_id = %s""",
                (assignment_id, student_user_id),
            )


def submit_assignment(assignment_id, student_user_id, answer):
    with get_db() as conn:
        with conn.cursor() as cursor:
            existing = _fetchone(
                cursor,
                """SELECT id FROM assignment_submissions
                   WHERE assignment_id = %s AND student_user_id = %s""",
                (assignment_id, student_user_id),
            )
            if existing:
                cursor.execute(
                    """UPDATE assignment_submissions
                       SET answer = %s, submitted_at = CURRENT_TIMESTAMP,
                           score = NULL, feedback = NULL, graded_at = NULL, mark_id = NULL
                       WHERE id = %s""",
                    (answer, existing["id"]),
                )
                return existing["id"]
            cursor.execute(
                """INSERT INTO assignment_submissions
                   (assignment_id, student_user_id, answer)
                   VALUES (%s, %s, %s)""",
                (assignment_id, student_user_id, answer),
            )
            return cursor.lastrowid


def get_submissions_for_assignment(assignment_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT s.*, u.full_name, sp.student_id
                   FROM assignment_submissions s
                   JOIN users u ON s.student_user_id = u.id
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE s.assignment_id = %s
                   ORDER BY s.submitted_at DESC""",
                (assignment_id,),
            )


def get_unsubmitted_students_for_assignment(assignment_id, class_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT u.id, u.full_name, sp.student_id
                   FROM class_enrollments ce
                   JOIN users u ON ce.student_user_id = u.id
                   LEFT JOIN student_profiles sp ON u.id = sp.user_id
                   WHERE ce.class_id = %s
                     AND u.id NOT IN (
                         SELECT student_user_id FROM assignment_submissions
                         WHERE assignment_id = %s
                     )
                   ORDER BY u.full_name""",
                (class_id, assignment_id),
            )


def grade_assignment_submission(submission_id, score, feedback, max_score, course_id, title, student_user_id):
    with get_db() as conn:
        with conn.cursor() as cursor:
            submission = _fetchone(
                cursor, "SELECT * FROM assignment_submissions WHERE id = %s", (submission_id,)
            )
            if not submission:
                return False

            mark_id = submission.get("mark_id")
            if mark_id:
                cursor.execute(
                    "UPDATE marks SET score = %s, max_score = %s WHERE id = %s",
                    (score, max_score, mark_id),
                )
            else:
                cursor.execute(
                    """INSERT INTO marks
                       (course_id, student_user_id, title, mark_type, score, max_score)
                       VALUES (%s, %s, %s, 'assignment', %s, %s)""",
                    (course_id, student_user_id, title, score, max_score),
                )
                mark_id = cursor.lastrowid

            cursor.execute(
                """UPDATE assignment_submissions
                   SET score = %s, feedback = %s, graded_at = CURRENT_TIMESTAMP, mark_id = %s
                   WHERE id = %s""",
                (score, feedback, mark_id, submission_id),
            )
            return True


def get_student_assignment_grades(student_user_id, class_id=None):
    with get_db() as conn:
        with conn.cursor() as cursor:
            sql = """SELECT a.title, a.max_score, a.deadline,
                            co.name AS course_name, c.name AS class_name,
                            s.score, s.feedback, s.graded_at, s.submitted_at
                     FROM assignment_submissions s
                     JOIN assignments a ON s.assignment_id = a.id
                     JOIN courses co ON a.course_id = co.id
                     JOIN classes c ON co.class_id = c.id
                     JOIN class_enrollments ce ON ce.class_id = c.id AND ce.student_user_id = %s
                     WHERE s.student_user_id = %s AND s.score IS NOT NULL"""
            params = [student_user_id, student_user_id]
            if class_id:
                sql += " AND c.id = %s"
                params.append(class_id)
            sql += " ORDER BY s.graded_at DESC"
            return _fetchall(cursor, sql, params)
