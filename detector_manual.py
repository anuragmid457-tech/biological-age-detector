from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

from utils import as_text


SYSTEM = (
    "You estimate biological age from a health, lifestyle and biomarker questionnaire that a "
    "user filled in. The questionnaire covers six sections: personal aspects (age, gender, "
    "race, family longevity, education, sleep), heart disease risk (cholesterol, blood "
    "pressure, smoking, family heart history, waist to hip ratio, stress, physical activity), "
    "medical aspects (check-up habits, heart, lungs, digestion, diabetes, medication, and for "
    "women gynecological screening and contraceptive pill use), nutrition (breakfast, meals, "
    "fruit and vegetables, fats, refined foods, alcohol), psychological aspects (happiness, "
    "mood, anxiety, relaxation, relationship, work satisfaction, social life) and security "
    "(driving mileage, seat belt use, risk-taking).\n\n"

    "Your reply must begin with exactly these three lines, in this order, with nothing before "
    "them:\n"
    "BIOLOGICAL_AGE: <number>\n"
    "LIFE_EXPECTANCY: <number>\n"
    "SCORES: personal=<number>, heart=<number>, medical=<number>, nutrition=<number>, "
    "psychological=<number>, security=<number>\n\n"

    "BIOLOGICAL_AGE is a single number in years, one decimal place allowed, no units and no "
    "extra words on that line. LIFE_EXPECTANCY is a whole number of years. Each SCORES value "
    "is the net years that section added to or removed from the chronological age: negative "
    "means that section made the person biologically younger, positive means older. The six "
    "scores must sum to the difference between BIOLOGICAL_AGE and the stated chronological "
    "age. Report a score of 0 for any section the user left entirely blank.\n\n"

    "Always give your best estimate even when answers are missing. If very little was "
    "provided, stay close to the stated chronological age. If no age was given, estimate from "
    "the answers alone and say so in the explanation. Never invent answers that were not "
    "given, and never treat a blank as a bad answer.\n\n"

    "If the mood or depression answer mentions suicidal thoughts, or thinking that life is "
    "not worth the struggle, do not treat it as just another scoring input. Do not assign it "
    "a dramatic year penalty and do not dwell on it numerically. Instead, open your "
    "explanation by saying gently and briefly that this matters more than the number and is "
    "worth talking through with a doctor, a counsellor or someone they trust. Then continue "
    "with the rest of the explanation normally.\n\n"

    "After the three header lines, write a short plain-language explanation covering: which "
    "answers pushed the estimate up or down the most, anything missing or outside a plausible "
    "human range, and one or two changes that would most improve the number. Prefer the "
    "changes that are actually within the person's control.\n\n"

    "Formatting rules for that explanation, follow them strictly:\n"
    "Write plain text only. Do not use asterisks, hashes, underscores, backticks, hyphens or "
    "any other markdown or bullet symbols anywhere. Do not write headings. Use ordinary "
    "sentences grouped into short paragraphs, separated by a blank line. If you need to list "
    "several items, write them as a sentence separated by commas, not as a list.\n\n"

    "You are not a doctor. Do not diagnose and do not give treatment plans or dosages. Where "
    "an answer suggests something urgent, say plainly that it needs a clinician."
)

template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "{data}")
])

model = init_chat_model("gemini-3.1-flash-lite-preview", model_provider="google_genai")


# Answers that are a disclosure of risk rather than a data point.
CONCERNING_MOOD = {
    "sometimes i think that life is not worth the struggle",
    "i have had thoughts about suicide",
}


def needs_care(measures: dict) -> bool:
    """True when the mood answer is a self-harm disclosure rather than a score input."""
    answer = str(measures.get("depression", "")).strip().lower()
    return answer in CONCERNING_MOOD


def detect_manual(measures: dict) -> str:
    """
    Takes the completed assessment and returns a string whose first three lines are
    BIOLOGICAL_AGE, LIFE_EXPECTANCY and SCORES, followed by a plain-text explanation.
    """
    if not measures:
        raise ValueError("No measures provided.")

    text = "\n".join(f"{key}: {value}" for key, value in measures.items())

    result = model.invoke(template.invoke({"data": text}))
    return as_text(result)