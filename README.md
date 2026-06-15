# EduPredict AI — Student Prediction System

An AI-powered web application that predicts student academic performance using machine learning. Built with Flask, MySQL, and scikit-learn.

## Features

- **Homepage** — Overview of the platform and how it works
- **About Page** — Technology details and performance tiers
- **Student Registration & Login** — Students create accounts and access their dashboard
- **Student Dashboard** — Run AI predictions and view history
- **Admin Dashboard** — Monitor all students and system-wide analytics
- **AI Predictions** — Random Forest model classifies students as At Risk, Average, or High Performer

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
├── config.py           # App configuration
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

Students must register via the **Register** page. Only students can self-register.

## Pages

| Route        | Description                    | Access        |
|--------------|--------------------------------|---------------|
| `/`          | Homepage                       | Public        |
| `/about`     | About the system               | Public        |
| `/login`     | Login page                     | Public        |
| `/register`  | Student registration           | Public        |
| `/student`   | Student prediction dashboard   | Students only |
| `/admin`     | Admin management dashboard     | Admin only    |

## Prediction Inputs

Students enter six metrics to receive a forecast:

1. Study hours per day
2. Attendance rate (%)
3. Previous GPA (0–4.0)
4. Assignments completed (out of 20)
5. Extracurricular hours per week
6. Sleep hours per night

## Database

The schema is defined in `database.sql`. Tables:

- `users` — Student and admin accounts
- `student_profiles` — Extended student information
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
