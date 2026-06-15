"""AI-based student performance prediction module."""

import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from config import MODEL_PATH

FEATURE_NAMES = [
    "study_hours",
    "attendance_rate",
    "previous_gpa",
    "assignments_completed",
    "extracurricular_hours",
    "sleep_hours",
]

LABELS = {0: "At Risk", 1: "Average", 2: "High Performer"}


def _generate_training_data():
    """Synthetic training data for the prediction model."""
    rng = np.random.default_rng(42)
    n_samples = 500

    study_hours = rng.uniform(1, 12, n_samples)
    attendance_rate = rng.uniform(40, 100, n_samples)
    previous_gpa = rng.uniform(1.5, 4.0, n_samples)
    assignments_completed = rng.integers(0, 21, n_samples)
    extracurricular_hours = rng.uniform(0, 15, n_samples)
    sleep_hours = rng.uniform(4, 10, n_samples)

    score = (
        study_hours * 0.15
        + attendance_rate * 0.02
        + previous_gpa * 0.35
        + assignments_completed * 0.08
        + extracurricular_hours * 0.05
        + sleep_hours * 0.1
    )

    labels = np.zeros(n_samples, dtype=int)
    labels[score >= 5.5] = 1
    labels[score >= 7.5] = 2

    X = np.column_stack([
        study_hours,
        attendance_rate,
        previous_gpa,
        assignments_completed,
        extracurricular_hours,
        sleep_hours,
    ])
    return X, labels


def train_and_save_model():
    """Train the Random Forest model and persist it to disk."""
    X, y = _generate_training_data()
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return model


def load_model():
    """Load the trained model, creating it if missing."""
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)
    return train_and_save_model()


def predict_student_performance(
    study_hours: float,
    attendance_rate: float,
    previous_gpa: float,
    assignments_completed: int,
    extracurricular_hours: float,
    sleep_hours: float,
) -> dict:
    """Run prediction and return result with confidence."""
    model = load_model()
    features = np.array([[
        study_hours,
        attendance_rate,
        previous_gpa,
        assignments_completed,
        extracurricular_hours,
        sleep_hours,
    ]])

    prediction = int(model.predict(features)[0])
    probabilities = model.predict_proba(features)[0]
    confidence = float(max(probabilities)) * 100

    recommendations = _get_recommendations(
        prediction,
        study_hours,
        attendance_rate,
        previous_gpa,
        assignments_completed,
        sleep_hours,
    )

    return {
        "result": LABELS[prediction],
        "confidence": round(confidence, 1),
        "recommendations": recommendations,
    }


def _get_recommendations(
    prediction: int,
    study_hours: float,
    attendance_rate: float,
    previous_gpa: float,
    assignments_completed: int,
    sleep_hours: float,
) -> list[str]:
    """Generate actionable recommendations based on inputs."""
    tips = []

    if study_hours < 4:
        tips.append("Increase daily study hours to at least 4–6 hours for better outcomes.")
    if attendance_rate < 75:
        tips.append("Improve class attendance — aim for 85% or higher.")
    if previous_gpa < 2.5:
        tips.append("Focus on foundational subjects to raise your GPA.")
    if assignments_completed < 12:
        tips.append("Complete more assignments on time to boost your performance score.")
    if sleep_hours < 6:
        tips.append("Prioritize 7–8 hours of sleep for better focus and retention.")

    if prediction == 2:
        tips.append("Excellent trajectory — maintain consistency and mentor peers.")
    elif prediction == 1:
        tips.append("You're on track — small improvements in weak areas can push you to top tier.")
    else:
        tips.append("Seek academic advising and form a structured study plan immediately.")

    return tips[:4]
