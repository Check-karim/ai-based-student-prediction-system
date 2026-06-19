# MKU Student Performance Predictor

An AI-powered web application for **Mount Kigali University (MKU)** that predicts student academic performance using machine learning. Built with Flask, MySQL, and scikit-learn.

## Features

- **Homepage** — Overview of the MKU prediction platform
- **About Page** — Technology details, performance tiers, and MKU integration
- **Student Registration & Login** — MKU students register with department and student ID
- **Student Dashboard** — Run AI predictions and view personal history
- **Admin Dashboard** — Monitor all students and system-wide analytics
- **Admin Prediction Tool** — Administrators can run the same AI forecast as students
- **AI Predictions** — Random Forest model classifies students as At Risk, Average, or High Performer
- **Reports** — Excel and PDF exports for administrators

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

Students must register via the **Register** page with their MKU department and student ID. Only students can self-register.

## Pages

| Route             | Description                         | Access        |
|-------------------|-------------------------------------|---------------|
| `/`               | Homepage                            | Public        |
| `/about`          | About the system                    | Public        |
| `/login`          | Login page                          | Public        |
| `/register`       | MKU student registration            | Public        |
| `/student`        | Student prediction dashboard        | Students only |
| `/admin`          | Admin overview and analytics        | Admin only    |
| `/admin/predict`  | Admin prediction tool               | Admin only    |
| `/admin/download/<format>` | Excel or PDF report export | Admin only    |

## Prediction Inputs

Students and administrators enter six metrics to receive a forecast:

1. Study hours per day
2. Attendance rate (%)
3. Previous GPA (0–4.0)
4. Assignments completed (out of 20)
5. Extracurricular hours per week
6. Sleep hours per night

## Mount Kigali University Integration

- Branding and copy reference **Mount Kigali University (MKU)**
- Registration uses official MKU departments (Business, IT, Education, Hospitality, Health Sciences, Law, etc.)
- Student profiles store MKU student ID, department, and year of study
- Predictions are linked to registered MKU student accounts (or the admin account for admin-run forecasts)

## Database

The schema is defined in `database.sql`. Tables:

- `users` — Student and admin accounts
- `student_profiles` — Extended MKU student information
- `predictions` — Prediction history

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
