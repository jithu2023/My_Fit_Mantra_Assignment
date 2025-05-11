# Workout Plan Generator

## Description

This project is a **Workout Plan Generator** designed to create a personalized 12-session workout plan for clients enrolled in a personal training package for 1 month. The plan consists of 3 sessions per week, structured into Warm-Up, Main Exercises, and Cool-Down sections. The application allows clients to optionally include either Circuit or Superset sections. Additionally, a progressive overload logic is implemented, meaning the number of sets and reps increases over time.

The workout plan is generated based on the user’s profile and preferences. Users can export their workout plan to a PDF format.

## Key Features

1. **User Profile Input**: The application accepts the following user profile details:

   * Name
   * Age
   * Gender
   * Goal (Weight Loss, Muscle Gain, Maintenance)
   * Experience Level (Beginner, Intermediate, Advanced)
   * Equipment List
   * Days per Week (1-7)
   * Optional: Include Circuit and Superset sections.

2. **Workout Plan Generation**:

   * Generates a 12-session workout plan (3 sessions per week).
   * Each session contains 3 sections: **Warm-Up**, **Main Exercises**, **Cool-Down**.
   * Optional Circuit or Superset sections can be included.
   * Progressive overload is applied for each session (increasing sets and reps).

3. **Progressive Overload**:

   * Adds sets and reps in a progressive manner for each session after the first 4 sessions (e.g., increases sets and reps to make the workout more challenging).

4. **Export to PDF**:

   * After generating the workout plan, users can download the plan as a PDF file.

5. **API Implementation**:

   * The backend is built with **FastAPI** to handle the generation of workout plans.
   * **Static files** (e.g., the HTML form) are served via FastAPI's static file serving capabilities.

6. **Frontend UI**:

   * A simple HTML form is used to collect user inputs for generating the workout plan.

7. **Exercise Sections**:

   * **Warm-Up**: Includes dynamic stretches and light cardio.
   * **Main Exercises**: Resistance training focused on muscle groups.
   * **Cool-Down**: Includes static stretching and deep breathing exercises.

## API Endpoint

The **Workout Plan Generator API** can be accessed at:

* [Render Deployment URL](https://my-fit-mantra-assignment-1.onrender.com/)

### POST `/generate-workout-plan`

This endpoint accepts a JSON object representing the user profile and returns a workout plan.

**Request Body**:

```json
{
  "name": "Aarav",
  "age": 35,
  "gender": "male",
  "goal": "muscle_gain",
  "experience": "intermediate",
  "equipment": ["dumbbells", "bench", "resistance_band"],
  "days_per_week": 3
}
```

**Response Body**:

```json
{
  "workout_plan": [
    {
      "session": 1,
      "date": "2025-05-06",
      "sections": [
        {
          "section": "Warm-Up",
          "exercises": [
            { "name": "Jumping Jacks", "duration": "2 min" },
            { "name": "Arm Circles", "sets": 2, "reps": 15 }
          ]
        },
        {
          "section": "Main workout",
          "exercises": [
            { "name": "Dumbbell Chest Press", "sets": 3, "reps": 10, "rest": "60s", "tempo": "2-1-1" },
            { "name": "Resistance Band Row", "sets": 3, "reps": 12 }
          ]
        },
        {
          "section": "Cool-Down",
          "exercises": [
            { "name": "Child’s Pose", "duration": "1 min" },
            { "name": "Chest Stretch", "duration": "30 sec each side" }
          ]
        }
      ]
    }
  ],
  "pdf_file": "static/workout_plan_Aarav.pdf"
}
```

**Response**:

* The response contains the workout plan details for each session.
* The PDF file can be downloaded from the `pdf_file` URL in the response.

## Usage

### 1. Run the FastAPI Server Locally:

1. Clone the repository:

   ```bash
   git clone https://github.com/jithu2023/My_Fit_Mantra_Assignment.git
   cd My_Fit_Mantra_Assignment
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:

   ```bash
   uvicorn main:app --reload
   ```

   The application will run on `http://127.0.0.1:8000`.

4. You can test the API by sending a POST request to `/generate-workout-plan`.

### 2. Access the Web Interface:

1. Open the `index.html` file in a browser or access it through the FastAPI server at `http://127.0.0.1:8000/` if running locally.

2. Fill in the details in the form and click the "Generate Workout Plan" button.

3. After the workout plan is generated, you will see the workout plan displayed in the results section, along with a button to download the PDF.

## Directory Structure

```
My_Fit_Mantra_Assignment/
│
├── static/              # Directory for static files (HTML, CSS, JS)
│   └── index.html       # Frontend HTML file
├── main.py              # FastAPI backend code
├── requirements.txt     # Python dependencies
└── README.md            # This README file
```

## Exercises and Logic

### 1. **Warm-Up**:

* Includes exercises like "Jumping Jacks" and "Arm Circles" for a fixed duration or reps.

### 2. **Main Exercises**:

* Selects a variety of exercises based on the user's experience level (e.g., "Bodyweight Squat", "Push-up", etc.).
* Adjusts sets and reps based on progressive overload for sessions after the first 4 weeks.

### 3. **Cool-Down**:

* Includes stretches like "Child's Pose" and "Chest Stretch".

### 4. **Progressive Overload**:

* For every session beyond the first 4, the sets and reps of each exercise are increased to ensure progressive overload.

### 5. **Optional Circuit/Superset**:

* If the user selects to include a circuit or superset, the corresponding exercises will be added to the plan.

---

## Links

* **GitHub Repository**: [https://github.com/jithu2023/My\_Fit\_Mantra\_Assignment](https://github.com/jithu2023/My_Fit_Mantra_Assignment)
* **Live Deployment**: [https://my-fit-mantra-assignment-1.onrender.com/](https://my-fit-mantra-assignment-1.onrender.com/)

---

