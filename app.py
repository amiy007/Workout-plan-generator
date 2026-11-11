"""Workout Plan Generator: Streamlit app that uses the Groq API (LLM) to build a weekly plan."""

import os
import random
from typing import List, Optional

import streamlit as st
from dotenv import load_dotenv
from groq import APIConnectionError, APIStatusError, AuthenticationError, Groq, RateLimitError

load_dotenv()

# ---------------------------------------------------------------- constants
GOALS: List[str] = ["Build muscle", "Lose fat", "General fitness", "Improve endurance"]
LEVELS: List[str] = ["Beginner", "Intermediate", "Advanced"]
EQUIPMENT: List[str] = ["No equipment", "Home dumbbells", "Full gym"]
# Model names change over time; override with GROQ_MODEL in .env if this one is retired.
DEFAULT_MODEL: str = "openai/gpt-oss-120b"

SYSTEM_PROMPT: str = """You are an experienced, safety-conscious personal trainer who writes \
practical weekly workout plans for real people.

HARD RULES (never break these):
1. Train on EXACTLY the number of days the user gives. All other days are labelled "Rest" \
(or "Active recovery" such as a walk). Do not add extra training days.
2. Use ONLY the equipment the user has. If "No equipment" is the only option, use bodyweight \
exercises only. If "Home dumbbells", use dumbbells and bodyweight only (no barbells, machines, \
cables). Never mention equipment the user does not have.
3. Respect injuries/limitations strictly: do not include any exercise that loads the affected \
area or movement. Choose safe alternatives instead and say briefly what you substituted.
4. Match the experience level: Beginner = simple movements, lower volume, longer rest; \
Intermediate = moderate volume and some progression; Advanced = higher volume/intensity, \
supersets or tempo work allowed.
5. Match the goal: Build muscle = hypertrophy rep ranges (6-12) with progressive overload; \
Lose fat = full-body/circuit emphasis plus some cardio; General fitness = balanced strength, \
cardio and mobility; Improve endurance = more cardio/conditioning plus muscular endurance work.
6. Make no medical claims, no diagnosis, no promises of specific results.
7. If (and only if) injuries/limitations were provided, end the plan with a one-sentence \
disclaimer: "This is general fitness information, not medical advice. Please consult a \
doctor or physiotherapist about your injury before starting."

OUTPUT FORMAT (Markdown, nothing else, no long intro):
## Weekly Overview
One or two sentences on the split you chose and why.

Then for each of the 7 days, in order:
### Day N: <Focus or "Rest">
- Warm-up: ...
- A table or list of exercises, each with: exercise name | sets x reps | rest time
- Cool-down: ...
Add one short "Tip" line at the end of each training day.

Finish with "## Progression Tips" (2-3 bullets)."""


# ---------------------------------------------------------------- logic
def validate_inputs(days: int, equipment: List[str]) -> Optional[str]:
    """Return a friendly error message if inputs are invalid, otherwise None."""
    if days < 1 or days > 7:
        return "Please choose between 1 and 7 training days per week."
    if not equipment:
        return "Please select at least one equipment option."
    return None


def get_api_key() -> Optional[str]:
    """Read the Groq API key from env vars (.env) or Streamlit secrets."""
    key = os.getenv("GROQ_API_KEY")
    if key:
        return key
    try:
        return st.secrets.get("GROQ_API_KEY")
    except Exception:
        return None


def build_user_prompt(
    goal: str,
    level: str,
    days: int,
    equipment: List[str],
    limitations: str,
    variation_seed: Optional[int] = None,
) -> str:
    """Turn the structured inputs into a clear, labelled prompt for the model."""
    limits = limitations.strip() or "None"
    prompt = (
        "Create a 7-day workout plan for this person:\n\n"
        f"- Fitness goal: {goal}\n"
        f"- Experience level: {level}\n"
        f"- Training days per week: {days} (so {7 - days} rest/recovery days)\n"
        f"- Equipment available: {', '.join(equipment)}\n"
        f"- Injuries or limitations: {limits}\n\n"
        "Follow every rule in your instructions."
    )
    if variation_seed is not None:
        prompt += (
            f"\n\nThis is a regeneration request (variation #{variation_seed}). "
            "Use a different exercise selection and split from a typical first answer, "
            "while still obeying all rules."
        )
    return prompt


def is_valid_plan(text: Optional[str], days: int) -> bool:
    """Basic sanity check on the LLM response."""
    if not text or len(text.strip()) < 200:
        return False
    return "day 1" in text.lower() and "day 7" in text.lower()


def generate_workout_plan(
    goal: str,
    level: str,
    days: int,
    equipment: List[str],
    limitations: str = "",
    variation_seed: Optional[int] = None,
) -> str:
    """Build the prompt, call Groq, and return the plan (or a friendly error message)."""
    error = validate_inputs(days, equipment)
    if error:
        return f"⚠️ {error}"

    api_key = get_api_key()
    if not api_key:
        return "⚠️ No Groq API key found. Add GROQ_API_KEY to your .env file and restart the app."

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(goal, level, days, equipment, limitations, variation_seed),
                },
            ],
            temperature=0.9 if variation_seed else 0.5,
            max_tokens=2500,
        )
        plan = response.choices[0].message.content if response.choices else None
    except AuthenticationError:
        return "⚠️ Your Groq API key looks invalid. Please check GROQ_API_KEY."
    except RateLimitError:
        return "⚠️ Rate limit reached. Please wait a minute and try again."
    except APIConnectionError:
        return "⚠️ Could not reach Groq. Please check your internet connection."
    except APIStatusError as exc:
        return f"⚠️ Groq returned an error (status {exc.status_code}). Please try again."
    except Exception:
        return "⚠️ Something went wrong while generating your plan. Please try again."

    if not is_valid_plan(plan, days):
        return "⚠️ The model returned an empty or incomplete plan. Please click Generate again."
    return plan  # type: ignore[return-value]


# ---------------------------------------------------------------- UI
def main() -> None:
    st.set_page_config(page_title="Workout Plan Generator", page_icon="💪", layout="centered")
    st.title("💪 Workout Plan Generator")
    st.caption("Tell us about yourself and get a weekly plan you can actually follow.")

    with st.form("inputs"):
        col1, col2 = st.columns(2)
        goal = col1.selectbox("Fitness goal", GOALS)
        level = col2.selectbox("Experience level", LEVELS)
        days = st.number_input("Days available per week", min_value=0, max_value=7, value=3, step=1)
        equipment = st.multiselect("Equipment access", EQUIPMENT, default=["Home dumbbells"])
        limitations = st.text_area(
            "Injuries or limitations (optional)",
            placeholder='e.g. "bad knees", "no overhead pressing"',
        )
        submitted = st.form_submit_button("Generate Plan", type="primary")

    if submitted:
        with st.spinner("Designing your plan..."):
            st.session_state["plan"] = generate_workout_plan(
                goal, level, int(days), equipment, limitations
            )
        st.session_state["last_inputs"] = (goal, level, int(days), equipment, limitations)

    plan: Optional[str] = st.session_state.get("plan")
    if plan:
        if plan.startswith("⚠️"):
            st.warning(plan)
        else:
            st.divider()
            st.markdown(plan)
            c1, c2 = st.columns(2)
            c1.download_button("⬇️ Download (.md)", plan, file_name="workout_plan.md", mime="text/markdown")
            if c2.button("🔄 Regenerate"):
                with st.spinner("Creating a variation..."):
                    st.session_state["plan"] = generate_workout_plan(
                        *st.session_state["last_inputs"], variation_seed=random.randint(1, 10_000)
                    )
                st.rerun()


if __name__ == "__main__":
    main()
