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
                        "admin@studentprediction.local",
                        generate_password_hash(ADMIN_PASSWORD),
                    ),
                )


def create_student(username, email, password, full_name, student_id, department, year_of_study):
    """Register a new student account."""
    password_hash = generate_password_hash(password)

    with get_db() as conn:
        with conn.cursor() as cursor:
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
            return user_id


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


def save_prediction(user_id, inputs, result, confidence):
    with get_db() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO predictions
                   (user_id, study_hours, attendance_rate, previous_gpa,
                    assignments_completed, extracurricular_hours, sleep_hours,
                    predicted_result, confidence_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    user_id,
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


def get_student_predictions(user_id, limit=10):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT * FROM predictions WHERE user_id = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (user_id, limit),
            )


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


def get_all_predictions(limit=50):
    with get_db() as conn:
        with conn.cursor() as cursor:
            return _fetchall(
                cursor,
                """SELECT p.*, u.username, u.full_name
                   FROM predictions p
                   JOIN users u ON p.user_id = u.id
                   ORDER BY p.created_at DESC LIMIT %s""",
                (limit,),
            )


def get_admin_stats():
    with get_db() as conn:
        with conn.cursor() as cursor:
            student_count = _fetchone(
                cursor, "SELECT COUNT(*) AS count FROM users WHERE role = 'student'"
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
