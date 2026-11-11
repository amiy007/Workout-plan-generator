# 💪 Workout Plan Generator

A single-page Streamlit app that turns structured fitness inputs into a personalized weekly workout plan using an LLM via the Groq API.

## Features
- Structured inputs: goal, experience level, days/week, equipment (multiselect), optional injuries
- Prompt engineered to respect equipment, injuries and training-day count, and to return a day-by-day Markdown plan
- Input validation (0 days, no equipment selected) and friendly handling of API failures and empty/malformed responses
- Stretch goals: Regenerate button, plan saved in `st.session_state`, download as `.md`

## Setup
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then paste your key from https://console.groq.com/keys
streamlit run app.py
```

## Prompt design notes
- **System prompt** holds the non-negotiable rules (exact training days, equipment-only exercises, injury avoidance, no medical claims, conditional disclaimer) plus the exact output format.
- **User prompt** passes inputs as labelled fields, and states the rest-day count explicitly so the model doesn't invent extra workouts.
- **Regenerate** raises temperature and adds a variation note to get a different plan.
- **Response check** rejects empty/too-short outputs or ones missing Day 1 / Day 7.

## Project structure
- `app.py`: UI + `generate_workout_plan()` and helpers
- `requirements.txt`, `.env.example`, `.gitignore`
