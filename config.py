import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Mount Kigali University branding
UNIVERSITY_NAME = "Mount Kigali University"
UNIVERSITY_SHORT = "MKU"
UNIVERSITY_EMAIL_DOMAIN = "mkur.ac.rw"
APP_NAME = "MKU Student Performance Predictor"

MKU_DEPARTMENTS = [
    "Business and Economics",
    "Education",
    "Informatics and Computing",
    "Journalism and Communication",
    "Travel and Tourism Management",
    "Hospitality and Events Management",
    "Nursing",
    "Medical Laboratory Sciences",
    "Midwifery",
    "Dental Technology",
    "Law",
]

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
SQL_SCHEMA_PATH = os.path.join(BASE_DIR, "database.sql")
MODEL_PATH = os.path.join(BASE_DIR, "models", "student_predictor.joblib")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "student_prediction")

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"
