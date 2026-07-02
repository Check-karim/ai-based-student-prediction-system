# MKU Student Performance Predictor

An AI-powered web application for **Mount Kigali University (MKU)** that predicts student academic performance using machine learning. Built with Flask, MySQL, and scikit-learn.

## Features

- **Homepage** — Overview of the MKU prediction platform
- **About Page** — Technology details, performance tiers, and MKU integration
- **Student Registration & Login** — MKU students register with department; Student ID is auto-generated
- **Student Dashboard** — View AI predictions (by class/course) and grades
- **Lecturer Login** — Lecturers log in with admin-created accounts
- **Lecturer Tools** — Create classes, assignments (with deadlines), add course marks, assign students, track attendance
- **Student Assignments** — View available assignments, submit answers before the deadline, and see marks and feedback
- **Admin Dashboard** — Monitor students, lecturers, classes, and system analytics
- **Admin Lecturer Management** — Create lecturer accounts (lecturers cannot self-register)
- **Admin Class Management** — Create classes and assign lecturers
- **Admin AI Prediction** — Run predictions by class (optionally per course), results shown per student
- **AI Predictions** — Random Forest model classifies students as At Risk, Average, or High Performer
- **Reports** — Excel and PDF exports for administrators

## User Roles

| Role | Access |
|------|--------|
| **Student** | Self-register, login, view predictions and grades by class/course |
| **Lecturer** | Login (admin-created account), create classes, manage marks, attendance, enroll students |
| **Admin** | Full system access — create lecturers/classes, run AI predictions by class |

### Auto-generated IDs

| ID type | Format | Example |
|---------|--------|---------|
| Student ID | `MKU-{year}-{sequence}` | `MKU-2026-001` |
| Employee ID | `EMP-{year}-{sequence}` | `EMP-2026-001` |
| Class code | `CLS-{year}-{sequence}` | `CLS-2026-001` |

IDs are assigned automatically on registration (students), when the admin creates a lecturer account, or when a class is created.

## Tech Stack

| Layer        | Technology              |
|--------------|-------------------------|
| Backend      | Python 3, Flask         |
| Database     | MySQL                   |
| ML           | scikit-learn, joblib    |
| Frontend     | HTML, CSS, JavaScript   |

## Project Structure

```
student prediction/
├── app.py              # Main Flask application
├── config.py           # App and MKU configuration
├── db.py               # Database helpers
├── database.sql        # SQL schema file
├── requirements.txt    # Python dependencies
├── ml/
│   └── predictor.py    # AI prediction module
├── templates/          # HTML templates
├── static/
│   ├── css/style.css
│   └── js/main.js
└── models/             # Trained ML model (auto-generated)
```

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- MySQL 8.0 or higher
- pip

### 2. Configure MySQL

Ensure MySQL is running, then set connection details via environment variables (or use the defaults):

| Variable         | Default              | Description        |
|------------------|----------------------|--------------------|
| `MYSQL_HOST`     | `localhost`          | MySQL server host  |
| `MYSQL_PORT`     | `3306`               | MySQL server port  |
| `MYSQL_USER`     | `root`               | MySQL username     |
| `MYSQL_PASSWORD` | *(empty)*            | MySQL password     |
| `MYSQL_DATABASE` | `student_prediction` | Database name      |

You can also initialize the schema manually:

```bash
mysql -u root -p < database.sql
```

### 3. Install Dependencies

```bash
cd "student prediction"
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

The MySQL database, tables, and ML model are created automatically on first run.

## Default Credentials

### Admin Account (predefined)

| Field    | Value  |
|----------|--------|
| Username | `admin` |
| Password | `admin` |

### Student Account

Students must register via the **Register** page with their MKU department and student ID.

### Lecturer Account

Lecturers are created by the admin via **Admin → Lecturers**. They cannot self-register.

## Typical Workflow

1. **Admin** creates lecturer accounts
2. **Lecturer** logs in, creates classes, publishes assignments with deadlines, enrolls students, records marks and attendance
3. **Student** views assignments, submits work before the deadline, and checks marks when graded
4. **Admin** runs AI prediction by class (optionally filtered by course) — results appear per student
5. **Student** views AI predictions filtered by class or course

## Pages

| Route | Description | Access |
|-------|-------------|--------|
| `/` | Homepage | Public |
| `/about` | About the system | Public |
| `/login` | Login page | Public |
| `/register` | MKU student registration | Public |
| `/student` | Student dashboard (predictions & grades) | Students |
| `/lecturer` | Lecturer dashboard — create and manage classes | Lecturers |
| `/lecturer/class/<id>` | Class detail — enroll students, courses | Lecturers |
| `/lecturer/class/<id>/marks` | Add course marks | Lecturers |
| `/lecturer/class/<id>/attendance` | Record attendance | Lecturers |
| `/lecturer/class/<id>/assignments` | Create assignments with deadlines | Lecturers |
| `/lecturer/assignment/<id>` | View submissions and grade students | Lecturers |
| `/student/assignments` | View available assignments and marks | Students |
| `/student/assignment/<id>` | Read instructions and submit work | Students |
| `/admin` | Admin overview | Admin |
| `/admin/lecturers` | Create/manage lecturers | Admin |
| `/admin/classes` | Create/manage classes | Admin |
| `/admin/predict` | Run AI prediction by class | Admin |
| `/admin/download/<format>` | Excel or PDF report | Admin |

## Prediction Inputs

When the admin runs a class prediction, the system builds inputs from lecturer-recorded data:

- **Attendance rate** — calculated from attendance sessions
- **Previous GPA** — derived from course marks
- **Assignments completed** — count of assignment marks (capped at 20)
- **Study hours, extracurricular hours, sleep hours** — default estimates when not recorded

## Database

The schema is defined in `database.sql`. Tables:

- `users` — Student, lecturer, and admin accounts
- `student_profiles` — Extended MKU student information
- `lecturer_profiles` — Lecturer employee ID and department
- `classes` — Academic classes assigned to lecturers
- `courses` — Courses within a class
- `class_enrollments` — Student enrollment in classes
- `marks` — Course marks entered by lecturers
- `attendance_sessions` / `attendance_records` — Attendance tracking
- `assignments` / `assignment_submissions` — Lecturer assignments, student submissions, and grades
- `predictions` — Prediction history (linked to class/course)

## Environment Variables (Optional)

| Variable         | Default              | Description          |
|------------------|----------------------|----------------------|
| `SECRET_KEY`     | dev secret           | Flask session key    |
| `MYSQL_HOST`     | `localhost`          | MySQL server host    |
| `MYSQL_PORT`     | `3306`               | MySQL server port    |
| `MYSQL_USER`     | `root`               | MySQL username       |
| `MYSQL_PASSWORD` | *(empty)*            | MySQL password       |
| `MYSQL_DATABASE` | `student_prediction` | Database name        |

## License

MIT — Free for educational use.
