-- Student Prediction System Database Schema
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS student_prediction
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE student_prediction;

-- Users table (students, lecturers, and admin)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin', 'lecturer') NOT NULL DEFAULT 'student',
    full_name VARCHAR(120),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_username (username),
    INDEX idx_users_role (role)
);

-- Student profiles (extended info for registered students)
CREATE TABLE IF NOT EXISTS student_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    student_id VARCHAR(50) UNIQUE,
    department VARCHAR(120),
    year_of_study INT DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Lecturer profiles (created by admin)
CREATE TABLE IF NOT EXISTS lecturer_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    employee_id VARCHAR(50) UNIQUE,
    department VARCHAR(120),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Academic classes (assigned to a lecturer)
CREATE TABLE IF NOT EXISTS classes (
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
);

-- Courses within a class
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    name VARCHAR(120) NOT NULL,
    code VARCHAR(50) NOT NULL,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    UNIQUE KEY uq_course_class_code (class_id, code),
    INDEX idx_courses_class (class_id)
);

-- Student enrollment in classes
CREATE TABLE IF NOT EXISTS class_enrollments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    student_user_id INT NOT NULL,
    enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_class_student (class_id, student_user_id),
    INDEX idx_enrollments_student (student_user_id)
);

-- Course marks entered by lecturers
CREATE TABLE IF NOT EXISTS marks (
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
);

-- Attendance sessions per class
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    class_id INT NOT NULL,
    session_date DATE NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
    INDEX idx_attendance_class (class_id)
);

-- Per-student attendance records
CREATE TABLE IF NOT EXISTS attendance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id INT NOT NULL,
    student_user_id INT NOT NULL,
    status ENUM('present', 'absent') NOT NULL DEFAULT 'present',
    FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (student_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uq_session_student (session_id, student_user_id),
    INDEX idx_attendance_student (student_user_id)
);

-- Assignments created by lecturers (linked to a course)
CREATE TABLE IF NOT EXISTS assignments (
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
);

-- Student assignment submissions and grades
CREATE TABLE IF NOT EXISTS assignment_submissions (
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
);

-- Prediction history (admin runs by class/course for students)
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    class_id INT,
    course_id INT,
    created_by_id INT,
    study_hours DOUBLE NOT NULL,
    attendance_rate DOUBLE NOT NULL,
    previous_gpa DOUBLE NOT NULL,
    assignments_completed INT NOT NULL,
    extracurricular_hours DOUBLE NOT NULL,
    sleep_hours DOUBLE NOT NULL,
    predicted_result VARCHAR(50) NOT NULL,
    confidence_score DOUBLE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_predictions_user_id (user_id),
    INDEX idx_predictions_class_id (class_id),
    INDEX idx_predictions_created_at (created_at)
);

-- Predefined admin account (created automatically on first run via init_db)
-- Username: admin | Password: admin
