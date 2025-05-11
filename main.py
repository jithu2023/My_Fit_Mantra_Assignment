from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Define your user profile model
class UserProfile(BaseModel):
    name: str
    age: int
    gender: str
    goal: str
    experience: str
    equipment: List[str]
    days_per_week: int
    include_circuit: Optional[bool] = False  # Optional field to include circuit training
    include_superset: Optional[bool] = False  # Optional field to include superset training

# Example warm-up and cooldown exercises
warmup_exercises = [
    {"name": "Jumping Jacks", "duration": "2 min"},
    {"name": "Arm Circles", "sets": 2, "reps": 15},
    {"name": "Mountain Climbers", "duration": "30 sec"},
    {"name": "Inchworm Walkouts", "sets": 2, "reps": 10},
    {"name": "Wall Angels", "sets": 2, "reps": 15}
]

cooldown_exercises = [
    {"name": "Child's Pose", "duration": "1 min"},
    {"name": "Chest Stretch", "duration": "30 sec each side"},
    {"name": "Hamstring Stretch", "duration": "30 sec"},
    {"name": "Seated Hamstring Stretch", "duration": "30 sec"},
    {"name": "Quad Stretch", "duration": "30 sec"},
    {"name": "Doorway Chest Stretch", "duration": "30 sec"}
]

main_exercises = {
    "beginner": [
        {"name": "Bodyweight Squat", "muscle_group": "legs", "sets": 3, "reps": 15, "tempo": "3-0-3"},
        {"name": "Push-up", "muscle_group": "chest", "sets": 3, "reps": 12, "tempo": "2-1-1"},
        {"name": "Plank", "muscle_group": "core", "sets": 3, "duration": "30 sec", "tempo": "5-0-5"},
        {"name": "Glute Bridge", "muscle_group": "glutes", "sets": 3, "reps": 15, "tempo": "2-0-2"},
        {"name": "Towel Rows", "muscle_group": "back", "sets": 3, "reps": 12, "tempo": "3-1-3"},
        {"name": "Triceps Dips", "muscle_group": "triceps", "sets": 3, "reps": 12, "tempo": "2-0-2"},
        {"name": "Leg Raises", "muscle_group": "core", "sets": 3, "reps": 15, "tempo": "2-0-2"},
        {"name": "Wall Sit", "muscle_group": "legs", "sets": 2, "duration": "30 sec", "tempo": "0-0-0"},
        {"name": "Dead Bug", "muscle_group": "core", "sets": 3, "reps": 15, "tempo": "3-0-3"},
        {"name": "Kneeling Shoulder Taps", "muscle_group": "core", "sets": 3, "reps": 20, "tempo": "2-1-1"}
    ]
}

@app.get("/", response_class=HTMLResponse)
def get_index():
    return FileResponse("static/index.html")

@app.post("/generate-workout-plan")
def generate_plan(user: UserProfile):
    plan = []
    start_date = datetime.today()
    session_gap = 7 // user.days_per_week
    overload_interval = 4

    if user.experience == "beginner":
        selected_exercises = main_exercises["beginner"]
    else:
        selected_exercises = main_exercises["beginner"]  # Placeholder for more levels

    for i in range(12):
        session_type = "push" if i % 2 == 0 else "pull"
        main = selected_exercises[:5]  # Select the first 5 exercises

        # Apply progressive overload
        if i >= overload_interval:
            for exercise in main:
                if 'sets' in exercise:
                    exercise['sets'] += 1
                if 'reps' in exercise:
                    exercise['reps'] += 2

        # Base sections
        sections = [
            {"section": "Warm-up", "exercises": warmup_exercises},
            {"section": "Main workout", "exercises": main},
            {"section": "Cooldown", "exercises": cooldown_exercises}
        ]

        # Optional section
        if user.include_circuit:
            circuit = [
                {"name": "Dumbbell Thrusters", "sets": 3, "reps": 15},
                {"name": "Jump Squats", "sets": 3, "reps": 15},
                {"name": "Mountain Climbers", "duration": "1 min"}
            ]
            sections.append({"section": "Circuit", "exercises": circuit})

        elif user.include_superset:
            superset = [
                {"name": "Dumbbell Bench Press + Dumbbell Row", "sets": 3, "reps": "10 each"},
                {"name": "Bicep Curl + Triceps Extension", "sets": 3, "reps": "12 each"}
            ]
            sections.append({"section": "Superset", "exercises": superset})

        session = {
            "session": i + 1,
            "date": (start_date + timedelta(days=i * session_gap)).strftime("%Y-%m-%d"),
            "sections": sections
        }

        plan.append(session)

    pdf_filename = f"workout_plan_{user.name}.pdf"
    pdf_filepath = generate_pdf(plan, pdf_filename)

    return {"workout_plan": plan, "pdf_file": pdf_filepath}

def generate_pdf(workout_plan, filename):
    pdf_filepath = f"static/{filename}"
    c = canvas.Canvas(pdf_filepath, pagesize=letter)
    c.setFont("Helvetica", 12)

    c.drawString(100, 750, "Workout Plan")
    y_position = 730

    for session in workout_plan:
        c.drawString(100, y_position, f"Session {session['session']} - {session['date']}")
        y_position -= 20
        for section in session["sections"]:
            c.drawString(100, y_position, f"{section['section']}:")
            y_position -= 20
            for exercise in section["exercises"]:
                detail = f"- {exercise['name']}"
                if 'sets' in exercise and 'reps' in exercise:
                    detail += f" ({exercise['sets']} sets, {exercise['reps']} reps)"
                elif 'sets' in exercise and 'duration' in exercise:
                    detail += f" ({exercise['sets']} sets, {exercise['duration']})"
                elif 'duration' in exercise:
                    detail += f" ({exercise['duration']})"
                c.drawString(120, y_position, detail)
                y_position -= 20
            y_position -= 10

        if y_position < 100:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = 750

    c.save()
    return pdf_filepath
