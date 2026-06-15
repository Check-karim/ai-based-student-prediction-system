-- Student Prediction System Database Schema
-- MySQL 8.0+

CREATE DATABASE IF NOT EXISTS student_prediction
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE student_prediction;

-- Users table (students and admin)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') NOT NULL DEFAULT 'student',
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

-- Prediction history
CREATE TABLE IF NOT EXISTS predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
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
    INDEX idx_predictions_user_id (user_id),
    INDEX idx_predictions_created_at (created_at)
);

-- Predefined admin account (created automatically on first run via init_db)
-- Username: admin | Password: admin
