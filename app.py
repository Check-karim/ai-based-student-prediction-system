"""Mount Kigali University — Student Performance Predictor (Flask app)."""

from datetime import datetime
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
    add_mark,
    authenticate_user,
    build_prediction_inputs,
    create_assignment,
    create_attendance_session,
    create_class,
    create_course,
    create_lecturer,
    create_student,
    email_exists,
    enroll_student_in_class,
    get_admin_stats,
    get_all_classes,
    get_all_lecturers,
    get_all_predictions,
    get_all_students,
    get_assignment_by_id,
    get_assignment_class_id,
    get_assignments_by_class,
    get_assignments_for_student,
    get_attendance_for_session,
    get_attendance_sessions,
    get_class_by_id,
    get_class_predictions,
    get_class_students,
    get_course_by_id,
    get_courses_by_class,
    get_lecturer_classes,
    get_lecturer_profile,
    get_marks_for_class,
    get_student_assignment_grades,
    get_student_classes,
    get_student_predictions,
    get_student_profile,
    get_submission,
    get_submission_by_id,
    get_submissions_for_assignment,
    get_unenrolled_students,
    get_unsubmitted_students_for_assignment,
    get_user_by_id,
    grade_assignment_submission,
    init_db,
    lecturer_owns_class,
    remove_student_from_class,
    save_attendance_records,
    save_prediction,
    student_enrolled_in_class,
    submit_assignment,
    username_exists,
)
from ml.predictor import predict_student_performance, train_and_save_model
from reports import generate_excel_report, generate_pdf_report
from validators import validate_email, validate_full_name, validate_username

app = Flask(__name__)
app.secret_key = SECRET_KEY

ROLE_DASHBOARDS = {
    "admin": "admin_dashboard",
    "lecturer": "lecturer_dashboard",
    "student": "student_dashboard",
}


@app.context_processor
def inject_university_config():
    return {
        "app_name": APP_NAME,
        "university_name": UNIVERSITY_NAME,
        "university_short": UNIVERSITY_SHORT,
        "university_email_domain": UNIVERSITY_EMAIL_DOMAIN,
        "mku_departments": MKU_DEPARTMENTS,
    }


def _redirect_for_role(role):
    endpoint = ROLE_DASHBOARDS.get(role, "home")
    return redirect(url_for(endpoint))


def _parse_deadline(deadline_str):
    """Parse datetime-local form value for MySQL."""
    return datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")


def _parse_assignment_deadline(deadline):
    if isinstance(deadline, datetime):
        return deadline
    text = str(deadline)[:19]
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid deadline: {deadline}")


def _assignment_is_open(assignment):
    """Check if assignment deadline has not passed."""
    return datetime.now() <= _parse_assignment_deadline(assignment["deadline"])


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
                return _redirect_for_role(user["role"])

            return f(*args, **kwargs)

        return wrapped

    return decorator


def _run_prediction_for_student(student_user_id, class_id, course_id, admin_id):
    """Run ML prediction for one student using class/course data."""
    inputs = build_prediction_inputs(student_user_id, class_id, course_id)
    prediction_result = predict_student_performance(**inputs)
    save_prediction(
        student_user_id,
        inputs,
        prediction_result["result"],
        prediction_result["confidence"],
        class_id=class_id,
        course_id=course_id,
        created_by_id=admin_id,
    )
    return {
        "student_user_id": student_user_id,
        "inputs": inputs,
        **prediction_result,
    }


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
        return _redirect_for_role(user["role"])

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
            return _redirect_for_role(user["role"])

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
        department = request.form.get("department", "").strip()
        year_of_study = request.form.get("year_of_study", "1")

        errors = []
        if not all([username, email, password, full_name, department]):
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

        _, student_id = create_student(
            username, email, password, full_name, department, year_of_study
        )
        flash(
            f"Registration successful! Your Student ID is {student_id}. Please log in.",
            "success",
        )
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ── Student routes ──────────────────────────────────────────────────────────

@app.route("/student")
@login_required(role="student")
def student_dashboard():
    user = get_user_by_id(session["user_id"])
    profile = get_student_profile(user["id"])
    classes = get_student_classes(user["id"])

    filter_class_id = request.args.get("class_id", type=int)
    filter_course_id = request.args.get("course_id", type=int)

    courses = []
    if filter_class_id:
        courses = get_courses_by_class(filter_class_id)

    history = get_student_predictions(
        user["id"],
        class_id=filter_class_id,
        course_id=filter_course_id,
    )

    marks = []
    if filter_class_id:
        marks = get_marks_for_class(filter_class_id, student_user_id=user["id"])

    assignment_grades = get_student_assignment_grades(user["id"], class_id=filter_class_id)

    return render_template(
        "student.html",
        user=user,
        profile=profile,
        classes=classes,
        courses=courses,
        history=history,
        marks=marks,
        assignment_grades=assignment_grades,
        filter_class_id=filter_class_id,
        filter_course_id=filter_course_id,
    )


@app.route("/student/assignments")
@login_required(role="student")
def student_assignments():
    user = get_user_by_id(session["user_id"])
    filter_class_id = request.args.get("class_id", type=int)
    assignments = get_assignments_for_student(user["id"], class_id=filter_class_id)
    classes = get_student_classes(user["id"])

    for item in assignments:
        if item.get("score") is not None:
            item["status"] = "Graded"
        elif item.get("submission_id"):
            item["status"] = "Submitted"
        elif _assignment_is_open(item):
            item["status"] = "Open"
        else:
            item["status"] = "Overdue"

    return render_template(
        "student_assignments.html",
        user=user,
        assignments=assignments,
        classes=classes,
        filter_class_id=filter_class_id,
    )


@app.route("/student/assignment/<int:assignment_id>", methods=["GET", "POST"])
@login_required(role="student")
def student_assignment(assignment_id):
    user = get_user_by_id(session["user_id"])
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        flash("Assignment not found.", "danger")
        return redirect(url_for("student_assignments"))

    if not student_enrolled_in_class(user["id"], assignment["class_id"]):
        flash("You are not enrolled in this class.", "danger")
        return redirect(url_for("student_assignments"))

    submission = get_submission(assignment_id, user["id"])
    is_open = _assignment_is_open(assignment)

    if request.method == "POST":
        answer = request.form.get("answer", "").strip()
        if not is_open:
            flash("The deadline for this assignment has passed.", "danger")
        elif not answer:
            flash("Please enter your answer before submitting.", "danger")
        else:
            submit_assignment(assignment_id, user["id"], answer)
            flash("Assignment submitted successfully.", "success")
            return redirect(url_for("student_assignment", assignment_id=assignment_id))

    return render_template(
        "student_assignment.html",
        user=user,
        assignment=assignment,
        submission=submission,
        is_open=is_open,
    )


# ── Lecturer routes ─────────────────────────────────────────────────────────

@app.route("/lecturer", methods=["GET", "POST"])
@login_required(role="lecturer")
def lecturer_dashboard():
    user = get_user_by_id(session["user_id"])
    profile = get_lecturer_profile(user["id"])

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        if not department and profile:
            department = profile.get("department") or ""
        academic_year = request.form.get("academic_year", "").strip()
        semester = request.form.get("semester", "").strip()

        if not all([name, department]):
            flash("Class name and department are required.", "danger")
        else:
            _, class_code = create_class(
                name, department, academic_year, semester, user["id"]
            )
            flash(
                f"Class '{name}' created (Code: {class_code}). "
                "You can now add courses and enroll students.",
                "success",
            )
            return redirect(url_for("lecturer_dashboard"))

    classes = get_lecturer_classes(user["id"])
    return render_template(
        "lecturer.html",
        user=user,
        profile=profile,
        classes=classes,
    )


@app.route("/lecturer/class/<int:class_id>")
@login_required(role="lecturer")
def lecturer_class_detail(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    class_info = get_class_by_id(class_id)
    students = get_class_students(class_id)
    unenrolled_students = get_unenrolled_students(class_id)
    courses = get_courses_by_class(class_id)
    sessions = get_attendance_sessions(class_id)

    return render_template(
        "lecturer_class.html",
        user=user,
        class_info=class_info,
        students=students,
        unenrolled_students=unenrolled_students,
        courses=courses,
        sessions=sessions,
    )


@app.route("/lecturer/class/<int:class_id>/enroll", methods=["POST"])
@login_required(role="lecturer")
def lecturer_enroll_student(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    student_id = request.form.get("student_id", type=int)
    if not student_id:
        flash("Please select a student.", "danger")
    else:
        try:
            enroll_student_in_class(class_id, student_id)
            flash("Student enrolled successfully.", "success")
        except Exception:
            flash("Student is already enrolled in this class.", "warning")

    return redirect(url_for("lecturer_class_detail", class_id=class_id))


@app.route("/lecturer/class/<int:class_id>/remove/<int:student_id>", methods=["POST"])
@login_required(role="lecturer")
def lecturer_remove_student(class_id, student_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    remove_student_from_class(class_id, student_id)
    flash("Student removed from class.", "info")
    return redirect(url_for("lecturer_class_detail", class_id=class_id))


@app.route("/lecturer/class/<int:class_id>/course", methods=["POST"])
@login_required(role="lecturer")
def lecturer_add_course(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    name = request.form.get("course_name", "").strip()
    code = request.form.get("course_code", "").strip()
    if not name or not code:
        flash("Course name and code are required.", "danger")
    else:
        try:
            create_course(class_id, name, code)
            flash(f"Course '{name}' added.", "success")
        except Exception:
            flash("A course with that code already exists in this class.", "danger")

    return redirect(url_for("lecturer_class_detail", class_id=class_id))


@app.route("/lecturer/class/<int:class_id>/marks", methods=["GET", "POST"])
@login_required(role="lecturer")
def lecturer_marks(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    class_info = get_class_by_id(class_id)
    students = get_class_students(class_id)
    courses = get_courses_by_class(class_id)

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        student_user_id = request.form.get("student_user_id", type=int)
        title = request.form.get("title", "").strip()
        mark_type = request.form.get("mark_type", "assignment")
        score = request.form.get("score", type=float)
        max_score = request.form.get("max_score", type=float, default=100)

        if not all([course_id, student_user_id, title, score is not None]):
            flash("All mark fields are required.", "danger")
        elif score < 0 or max_score <= 0 or score > max_score:
            flash("Invalid score values.", "danger")
        else:
            add_mark(course_id, student_user_id, title, mark_type, score, max_score)
            flash("Mark recorded successfully.", "success")
            return redirect(url_for("lecturer_marks", class_id=class_id))

    marks = get_marks_for_class(class_id)
    return render_template(
        "lecturer_marks.html",
        user=user,
        class_info=class_info,
        students=students,
        courses=courses,
        marks=marks,
    )


@app.route("/lecturer/class/<int:class_id>/attendance", methods=["GET", "POST"])
@login_required(role="lecturer")
def lecturer_attendance(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    class_info = get_class_by_id(class_id)
    students = get_class_students(class_id)
    sessions = get_attendance_sessions(class_id)

    if request.method == "POST":
        session_date = request.form.get("session_date", "").strip()
        note = request.form.get("note", "").strip() or None

        if not session_date:
            flash("Session date is required.", "danger")
        elif not students:
            flash("Enroll students before recording attendance.", "warning")
        else:
            session_id = create_attendance_session(class_id, session_date, note)
            records = []
            for student in students:
                status = request.form.get(f"status_{student['id']}", "absent")
                records.append((student["id"], status))
            save_attendance_records(session_id, records)
            flash("Attendance recorded successfully.", "success")
            return redirect(url_for("lecturer_attendance", class_id=class_id))

    return render_template(
        "lecturer_attendance.html",
        user=user,
        class_info=class_info,
        students=students,
        sessions=sessions,
    )


@app.route("/lecturer/class/<int:class_id>/assignments", methods=["GET", "POST"])
@login_required(role="lecturer")
def lecturer_assignments(class_id):
    user = get_user_by_id(session["user_id"])
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this class.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    class_info = get_class_by_id(class_id)
    courses = get_courses_by_class(class_id)
    assignments = get_assignments_by_class(class_id)

    if request.method == "POST":
        course_id = request.form.get("course_id", type=int)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        deadline_str = request.form.get("deadline", "").strip()
        max_score = request.form.get("max_score", type=float, default=100)

        if not all([course_id, title, deadline_str]):
            flash("Course, title, and deadline are required.", "danger")
        elif max_score <= 0:
            flash("Max score must be greater than zero.", "danger")
        else:
            try:
                deadline = _parse_deadline(deadline_str)
                create_assignment(course_id, title, description, deadline, max_score)
                flash(f"Assignment '{title}' created.", "success")
                return redirect(url_for("lecturer_assignments", class_id=class_id))
            except ValueError:
                flash("Invalid deadline format.", "danger")

    return render_template(
        "lecturer_assignments.html",
        user=user,
        class_info=class_info,
        courses=courses,
        assignments=assignments,
    )


@app.route("/lecturer/assignment/<int:assignment_id>", methods=["GET", "POST"])
@login_required(role="lecturer")
def lecturer_assignment_detail(assignment_id):
    user = get_user_by_id(session["user_id"])
    assignment = get_assignment_by_id(assignment_id)
    if not assignment:
        flash("Assignment not found.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    class_id = assignment["class_id"]
    if not lecturer_owns_class(user["id"], class_id):
        flash("You do not have access to this assignment.", "danger")
        return redirect(url_for("lecturer_dashboard"))

    if request.method == "POST":
        submission_id = request.form.get("submission_id", type=int)
        score = request.form.get("score", type=float)
        feedback = request.form.get("feedback", "").strip() or None

        if not submission_id or score is None:
            flash("Submission and score are required.", "danger")
        elif score < 0 or score > assignment["max_score"]:
            flash(f"Score must be between 0 and {assignment['max_score']}.", "danger")
        else:
            submission = get_submission_by_id(submission_id)
            if not submission or submission["assignment_id"] != assignment_id:
                flash("Submission not found.", "danger")
            else:
                grade_assignment_submission(
                    submission_id,
                    score,
                    feedback,
                    assignment["max_score"],
                    assignment["course_id"],
                    assignment["title"],
                    submission["student_user_id"],
                )
                flash("Submission graded successfully.", "success")
                return redirect(url_for("lecturer_assignment_detail", assignment_id=assignment_id))

    submissions = get_submissions_for_assignment(assignment_id)
    missing = get_unsubmitted_students_for_assignment(assignment_id, class_id)

    return render_template(
        "lecturer_assignment_detail.html",
        user=user,
        assignment=assignment,
        submissions=submissions,
        missing=missing,
    )


# ── Admin routes ────────────────────────────────────────────────────────────

@app.route("/admin")
@login_required(role="admin")
def admin_dashboard():
    stats = get_admin_stats()
    students = get_all_students()
    predictions = get_all_predictions()
    lecturers = get_all_lecturers()
    classes = get_all_classes()
    return render_template(
        "admin.html",
        stats=stats,
        students=students,
        predictions=predictions,
        lecturers=lecturers,
        classes=classes,
    )


@app.route("/admin/lecturers", methods=["GET", "POST"])
@login_required(role="admin")
def admin_lecturers():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        department = request.form.get("department", "").strip()

        errors = []
        if not all([username, email, password, full_name, department]):
            errors.append("All fields are required.")
        errors.extend(validate_username(username))
        errors.extend(validate_full_name(full_name))
        errors.extend(validate_email(email))
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if username_exists(username):
            errors.append("Username already taken.")
        if email_exists(email):
            errors.append("Email already registered.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            _, employee_id = create_lecturer(
                username, email, password, full_name, department
            )
            flash(
                f"Lecturer account created for {full_name}. "
                f"Employee ID: {employee_id}. They can now log in.",
                "success",
            )
            return redirect(url_for("admin_lecturers"))

    lecturers = get_all_lecturers()
    return render_template("admin_lecturers.html", lecturers=lecturers)


@app.route("/admin/classes", methods=["GET", "POST"])
@login_required(role="admin")
def admin_classes():
    lecturers = get_all_lecturers()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        academic_year = request.form.get("academic_year", "").strip()
        semester = request.form.get("semester", "").strip()
        lecturer_id = request.form.get("lecturer_id", type=int)

        if not all([name, department, lecturer_id]):
            flash("Class name, department, and lecturer are required.", "danger")
        else:
            _, class_code = create_class(
                name, department, academic_year, semester, lecturer_id
            )
            flash(
                f"Class '{name}' created (Code: {class_code}) and assigned to lecturer.",
                "success",
            )
            return redirect(url_for("admin_classes"))

    classes = get_all_classes()
    return render_template(
        "admin_classes.html",
        classes=classes,
        lecturers=lecturers,
    )


@app.route("/admin/predict", methods=["GET", "POST"])
@login_required(role="admin")
def admin_predict():
    classes = get_all_classes()
    selected_class_id = request.args.get("class_id", type=int) or request.form.get("class_id", type=int)
    selected_course_id = request.args.get("course_id", type=int) or request.form.get("course_id", type=int)

    class_info = None
    courses = []
    students = []
    results = []

    if selected_class_id:
        class_info = get_class_by_id(selected_class_id)
        courses = get_courses_by_class(selected_class_id)
        students = get_class_students(selected_class_id)

    if request.method == "POST" and selected_class_id:
        if not students:
            flash("No students enrolled in this class. Enroll students first.", "warning")
        else:
            admin_user = get_user_by_id(session["user_id"])
            results = []
            for student in students:
                result = _run_prediction_for_student(
                    student["id"],
                    selected_class_id,
                    selected_course_id or None,
                    admin_user["id"],
                )
                result["student_name"] = student["full_name"]
                result["student_id"] = student.get("student_id", "")
                results.append(result)

            scope = "class"
            if selected_course_id:
                course = get_course_by_id(selected_course_id)
                scope = f"course ({course['name']})" if course else "course"
            flash(
                f"AI predictions completed for {len(results)} students by {scope}.",
                "success",
            )

    if selected_class_id and not results:
        results = get_class_predictions(selected_class_id, selected_course_id or None)

    return render_template(
        "admin_predict.html",
        classes=classes,
        class_info=class_info,
        courses=courses,
        students=students,
        results=results,
        selected_class_id=selected_class_id,
        selected_course_id=selected_course_id,
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
