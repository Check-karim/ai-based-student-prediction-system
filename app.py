"""Mount Kigali University — Student Performance Predictor (Flask app)."""

from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from config import (
    APP_NAME,
    MKU_DEPARTMENTS,
    SECRET_KEY,
    UNIVERSITY_EMAIL_DOMAIN,
    UNIVERSITY_NAME,
    UNIVERSITY_SHORT,
)
from db import (
    authenticate_user,
    create_student,
    email_exists,
    get_admin_stats,
    get_all_predictions,
    get_all_students,
    get_student_predictions,
    get_student_profile,
    get_user_by_id,
    init_db,
    save_prediction,
    username_exists,
)
from ml.predictor import predict_student_performance, train_and_save_model
from reports import generate_excel_report, generate_pdf_report
from validators import validate_email, validate_full_name, validate_username

app = Flask(__name__)
app.secret_key = SECRET_KEY


@app.context_processor
def inject_university_config():
    return {
        "app_name": APP_NAME,
        "university_name": UNIVERSITY_NAME,
        "university_short": UNIVERSITY_SHORT,
        "university_email_domain": UNIVERSITY_EMAIL_DOMAIN,
        "mku_departments": MKU_DEPARTMENTS,
    }


def _process_prediction_form(user_id):
    """Parse form, run ML prediction, save result. Returns (result_dict|None, error_flashed)."""
    try:
        inputs = {
            "study_hours": float(request.form.get("study_hours", 0)),
            "attendance_rate": float(request.form.get("attendance_rate", 0)),
            "previous_gpa": float(request.form.get("previous_gpa", 0)),
            "assignments_completed": int(request.form.get("assignments_completed", 0)),
            "extracurricular_hours": float(request.form.get("extracurricular_hours", 0)),
            "sleep_hours": float(request.form.get("sleep_hours", 0)),
        }

        if not (0 <= inputs["attendance_rate"] <= 100):
            flash("Attendance rate must be between 0 and 100.", "danger")
            return None, True
        if not (0 <= inputs["previous_gpa"] <= 4.0):
            flash("GPA must be between 0 and 4.0.", "danger")
            return None, True

        prediction_result = predict_student_performance(**inputs)
        save_prediction(
            user_id,
            inputs,
            prediction_result["result"],
            prediction_result["confidence"],
        )
        flash("Prediction completed successfully!", "success")
        return prediction_result, False
    except (ValueError, TypeError):
        flash("Please enter valid numeric values.", "danger")
        return None, True


def login_required(role=None):
    """Decorator to protect routes by login status and optional role."""

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            user_id = session.get("user_id")
            if not user_id:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))

            user = get_user_by_id(user_id)
            if not user:
                session.clear()
                flash("Session expired. Please log in again.", "warning")
                return redirect(url_for("login"))

            if role and user["role"] != role:
                flash("You do not have permission to access that page.", "danger")
                if user["role"] == "admin":
                    return redirect(url_for("admin_dashboard"))
                return redirect(url_for("student_dashboard"))

            return f(*args, **kwargs)

        return wrapped

    return decorator


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        user = get_user_by_id(session["user_id"])
        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template("login.html")

        user = authenticate_user(username, password)
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['full_name'] or user['username']}!", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("student_dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        full_name = request.form.get("full_name", "").strip()
        student_id = request.form.get("student_id", "").strip()
        department = request.form.get("department", "").strip()
        year_of_study = request.form.get("year_of_study", "1")

        errors = []
        if not all([username, email, password, full_name, student_id, department]):
            errors.append("All fields are required.")
        errors.extend(validate_username(username))
        errors.extend(validate_full_name(full_name))
        errors.extend(validate_email(email))
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if username_exists(username):
            errors.append("Username already taken.")
        if email_exists(email):
            errors.append("Email already registered.")

        try:
            year_of_study = int(year_of_study)
            if year_of_study < 1 or year_of_study > 6:
                errors.append("Year of study must be between 1 and 6.")
        except ValueError:
            errors.append("Invalid year of study.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html")

        create_student(
            username, email, password, full_name, student_id, department, year_of_study
        )
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


@app.route("/student", methods=["GET", "POST"])
@login_required(role="student")
def student_dashboard():
    user = get_user_by_id(session["user_id"])
    profile = get_student_profile(user["id"])
    prediction_result = None
    history = get_student_predictions(user["id"])

    if request.method == "POST":
        prediction_result, _ = _process_prediction_form(user["id"])
        if prediction_result:
            history = get_student_predictions(user["id"])

    return render_template(
        "student.html",
        user=user,
        profile=profile,
        prediction_result=prediction_result,
        history=history,
    )


@app.route("/admin/predict", methods=["GET", "POST"])
@login_required(role="admin")
def admin_predict():
    user = get_user_by_id(session["user_id"])
    prediction_result = None
    history = get_student_predictions(user["id"], limit=10)

    if request.method == "POST":
        prediction_result, _ = _process_prediction_form(user["id"])
        if prediction_result:
            history = get_student_predictions(user["id"], limit=10)

    return render_template(
        "admin_predict.html",
        user=user,
        prediction_result=prediction_result,
        history=history,
    )


@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    stats = get_admin_stats()
    students = get_all_students()
    predictions = get_all_predictions()
    return render_template(
        "admin.html",
        stats=stats,
        students=students,
        predictions=predictions,
    )


@app.route("/admin/download/<report_format>")
@login_required(role="admin")
def admin_download_report(report_format):
    stats = get_admin_stats()
    students = get_all_students()
    predictions = get_all_predictions(limit=10000)

    if report_format == "excel":
        buffer = generate_excel_report(stats, students, predictions)
        return send_file(
            buffer,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="mku_prediction_report.xlsx",
        )

    if report_format == "pdf":
        buffer = generate_pdf_report(stats, students, predictions)
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="mku_prediction_report.pdf",
        )

    flash("Invalid report format.", "danger")
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    init_db()
    train_and_save_model()
    app.run(debug=True, host="0.0.0.0", port=5000)
