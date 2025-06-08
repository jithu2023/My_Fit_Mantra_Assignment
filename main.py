from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from openai import OpenAI
import traceback
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import sessionmaker, declarative_base, Session
import re
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Debug environment variables
logger.info("Environment variables:")
for key in ['OPENAI_API_KEY', 'PATH']:
    value = os.getenv(key)
    masked_value = value[:4] + '...' + value[-4:] if value and len(value) > 8 else value
    logger.info(f"  {key}: {masked_value}")

# Create static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

# --- DATABASE SETUP ---
DATABASE_URL = "sqlite:///./workout.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

Base = declarative_base()

class UserWorkoutHistory(Base):
    __tablename__ = "user_workout_history"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    workout_plan = Column(JSON)
    feedback = Column(JSON, nullable=True)

Base.metadata.create_all(bind=engine)

# --- Pydantic models ---
class UserProfile(BaseModel):
    name: str
    age: int
    gender: str
    goal: str
    experience: str
    equipment: List[str] = []
    days_per_week: int
    include_circuit: Optional[bool] = False
    include_superset: Optional[bool] = False

class Feedback(BaseModel):
    difficulty: Optional[str] = None
    soreness: Optional[str] = None
    energy_level: Optional[str] = None

class WorkoutRequest(BaseModel):
    profile: UserProfile
    previous_feedback: Optional[Feedback] = None

# --- Static exercises ---
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

# --- Helper functions ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def adjust_workout_based_on_feedback(feedback: Optional[Feedback], workout_plan: List[dict]) -> List[dict]:
    if not feedback:
        return workout_plan

    for ex in workout_plan:
        if isinstance(ex, dict):
            if 'sets' in ex and isinstance(ex['sets'], int):
                if feedback.difficulty == 'easy':
                    ex['sets'] = max(1, ex['sets'] - 1)
                elif feedback.difficulty == 'hard':
                    ex['sets'] += 1

            if 'reps' in ex and isinstance(ex['reps'], int):
                if feedback.difficulty == 'easy':
                    ex['reps'] = max(5, ex['reps'] - 3)
                elif feedback.difficulty == 'hard':
                    ex['reps'] += 3

            if 'duration' in ex and isinstance(ex['duration'], str):
                if feedback.soreness == 'severe':
                    try:
                        time_str = ex['duration'].split()[0]
                        time_val = int(time_str)
                        reduced = max(10, int(time_val * 0.75))
                        ex['duration'] = ex['duration'].replace(time_str, str(reduced))
                    except Exception:
                        pass
    return workout_plan

# FIXED: Removed duplicate prompt assignment
def build_prompt(user: UserProfile, previous_sessions: List[UserWorkoutHistory], feedback: Optional[Feedback]) -> str:
    prompt = (
        f"Create a workout plan with exactly 5 exercises for a {user.age}-year-old {user.gender} "
        f"with {user.experience} experience level. Goal: {user.goal}. "
        f"Available equipment: {', '.join(user.equipment) if user.equipment else 'none'}. "
        f"Workout days per week: {user.days_per_week}.\n"
    )

    if previous_sessions:
        prompt += "\nPrevious workouts:\n"
        for session in previous_sessions[-3:]:
            prompt += f"- {session.date.strftime('%Y-%m-%d')}: {session.workout_plan}\n"
            if session.feedback:
                prompt += f"  Feedback: {session.feedback}\n"

    if feedback:
        prompt += f"\nCurrent feedback: Difficulty={feedback.difficulty}, Soreness={feedback.soreness}, Energy={feedback.energy_level}\n"

    prompt += (
        "\nFormat each exercise as: Name - Description\n"
        "Include in the description: muscle group, sets, reps or duration\n"
        "Example: Push-ups - Chest and triceps, 3 sets x 12 reps\n"
    )
    
    if user.include_circuit:
        prompt += "Structure as 2 circuits with 2 exercises each.\n"
    elif user.include_superset:
        prompt += "Structure as 2 supersets with 2 exercises each.\n"
    
    return prompt

# --- OpenAI Client Initialization ---
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Enhanced debugging
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set")
        logger.error("Current working directory: %s", os.getcwd())
        logger.error("Files in current directory: %s", os.listdir('.'))
        logger.error("Environment variables: %s", {k: v for k, v in os.environ.items() if 'OPENAI' in k})
        
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY environment variable not set. Please set your OpenAI API key."
        )
    
    # Check if key looks valid
    if not api_key.startswith("sk-") or len(api_key) < 40:
        logger.error("OPENAI_API_KEY appears invalid. Should start with 'sk-' and be at least 40 characters")
        logger.error("Key value: %s...%s", api_key[:4], api_key[-4:])
        
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY appears invalid. Should start with 'sk-' and be at least 40 characters"
        )
    
    return OpenAI(api_key=api_key)

# --- Generate workout using OpenAI ---
def generate_openai_workout(user: UserProfile, prompt: str) -> List[dict]:
    try:
        logger.info("Calling OpenAI API with prompt")
        client = get_openai_client()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Using gpt-3.5-turbo
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800
        )
        content = response.choices[0].message.content
        logger.info(f"OpenAI response content: {content[:200]}...")  # Log first 200 chars
        
        exercises = []
        
        for line in content.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            if '-' in line or '–' in line:
                parts = line.split('–') if '–' in line else line.split('-')
                name = parts[0].strip()
                details = parts[1].strip() if len(parts) > 1 else ""
                ex = {"name": name}

                sets_match = re.search(r'(\d+)\s*sets?', details)
                reps_match = re.search(r'(\d+)\s*reps?', details)
                duration_match = re.search(r'(\d+\s*(sec|min|minutes|seconds))', details, re.IGNORECASE)

                if sets_match:
                    ex["sets"] = int(sets_match.group(1))
                if reps_match:
                    ex["reps"] = int(reps_match.group(1))
                if duration_match:
                    ex["duration"] = duration_match.group(1)

                ex["details"] = details
                exercises.append(ex)
                logger.info(f"Parsed exercise: {ex['name']}")

        logger.info(f"Total exercises parsed: {len(exercises)}")

        if user.include_circuit and len(exercises) >= 4:
            exercises = [
                {"name": "Circuit Round 1", "exercises": exercises[:2]},
                {"name": "Circuit Round 2", "exercises": exercises[2:4]}
            ]
            logger.info("Formatted as circuits")
        elif user.include_superset and len(exercises) >= 4:
            exercises = [
                {"name": "Superset 1", "exercises": [exercises[0], exercises[1]]},
                {"name": "Superset 2", "exercises": [exercises[2], exercises[3]]}
            ]
            logger.info("Formatted as supersets")
        else:
            exercises = exercises[:5]
            logger.info("Using first 5 exercises")

        return exercises
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        logger.error(traceback.format_exc())
        # Provide more user-friendly error message
        error_detail = f"OpenAI API error: {str(e)}"
        if "insufficient_quota" in str(e):
            error_detail = "Your OpenAI account has no remaining credits. Please add payment method to your OpenAI account."
        elif "model_not_found" in str(e):
            error_detail = "The requested AI model is not available. Using GPT-3.5-turbo instead."
        raise HTTPException(status_code=500, detail=error_detail)

def generate_pdf(workout_plan: List[dict], filename: str) -> str:
    try:
        logger.info(f"Generating PDF: {filename}")
        pdf_filepath = os.path.join("static", filename)
        c = canvas.Canvas(pdf_filepath, pagesize=letter)
        c.setFont("Helvetica", 12)

        c.drawString(100, 750, "Workout Plan")
        y_position = 730
        line_height = 15
        page_height = 750
        bottom_margin = 50

        for session_idx, session in enumerate(workout_plan, start=1):
            section_title = session.get("section", f"Section {session_idx}")
            c.drawString(100, y_position, f"{section_title}:")
            y_position -= line_height

            for ex in session.get("exercises", []):
                if "exercises" in ex:
                    c.drawString(110, y_position, f"{ex['name']}:")
                    y_position -= line_height
                    for sub_ex in ex["exercises"]:
                        detail = f"- {sub_ex['name']}"
                        if 'sets' in sub_ex and 'reps' in sub_ex:
                            detail += f", {sub_ex['sets']} sets x {sub_ex['reps']} reps"
                        elif 'duration' in sub_ex:
                            detail += f", {sub_ex['duration']}"
                        elif 'details' in sub_ex:
                            detail += f", {sub_ex['details']}"
                        c.drawString(120, y_position, detail)
                        y_position -= line_height
                        if y_position < bottom_margin:
                            c.showPage()
                            c.setFont("Helvetica", 12)
                            y_position = page_height
                else:
                    detail = f"- {ex['name']}"
                    if 'sets' in ex and 'reps' in ex:
                        detail += f", {ex['sets']} sets x {ex['reps']} reps"
                    elif 'duration' in ex:
                        detail += f", {ex['duration']}"
                    elif 'details' in ex:
                        detail += f", {ex['details']}"
                    c.drawString(110, y_position, detail)
                    y_position -= line_height
                    if y_position < bottom_margin:
                        c.showPage()
                        c.setFont("Helvetica", 12)
                        y_position = page_height

        c.save()
        logger.info(f"PDF generated at: {pdf_filepath}")
        return pdf_filepath
    except Exception as e:
        logger.error(f"PDF generation failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

# --- API endpoint ---
@app.post("/generate-workout-plan")
def generate_workout_plan(request: WorkoutRequest, db: Session = Depends(get_db)):
    try:
        logger.info("Received workout generation request")
        user = request.profile
        feedback = request.previous_feedback
        logger.info(f"User: {user.name}, Goal: {user.goal}, Experience: {user.experience}")

        previous_sessions = db.query(UserWorkoutHistory).filter(
            UserWorkoutHistory.user_name == user.name
        ).order_by(UserWorkoutHistory.date.desc()).limit(3).all()
        logger.info(f"Found {len(previous_sessions)} previous sessions")

        prompt = build_prompt(user, previous_sessions, feedback)
        logger.info(f"Prompt: {prompt[:200]}...")  # Log first 200 chars
        
        main_workout = generate_openai_workout(user, prompt)
        logger.info("Generated main workout")

        workout_plan = [
            {"section": "Warm-up", "exercises": warmup_exercises},
            {"section": "Main Workout", "exercises": main_workout},
            {"section": "Cool-down", "exercises": cooldown_exercises}
        ]

        workout_plan[1]["exercises"] = adjust_workout_based_on_feedback(feedback, workout_plan[1]["exercises"])
        logger.info("Adjusted workout based on feedback")

        new_record = UserWorkoutHistory(
            user_name=user.name,
            workout_plan=workout_plan,
            feedback=feedback.dict() if feedback else None
        )
        db.add(new_record)
        db.commit()
        logger.info("Saved workout to database")

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"workout_{user.name.replace(' ', '_')}_{timestamp}.pdf"
        pdf_path = generate_pdf(workout_plan, pdf_filename)
        logger.info("PDF generated")

        return {
            "message": "Workout plan generated successfully",
            "user": user.name,
            "workout_plan": workout_plan,
            "pdf_file": pdf_filename
        }
    except HTTPException as e:
        logger.error(f"HTTPException: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Mount static files last
app.mount("/", StaticFiles(directory="static", html=True), name="static")