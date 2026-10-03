from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate

from learning import examples_for
from questions import describe_answers
from utils import as_text


SYSTEM = (
    "You estimate biological age from a health, lifestyle and biomarker questionnaire that a "
    "user filled in. Every question is optional, so expect gaps. The questionnaire covers six "
    "scored sections: personal aspects (age, gender, ethnicity, height and weight, family "
    "longevity, education, sleep), heart disease risk (cholesterol, blood pressure, resting "
    "heart rate, smoking and other tobacco, family heart history, waist to hip ratio, stress, "
    "physical activity), medical aspects (check-up habits, heart, lungs, digestion, diabetes, "
    "medication, and for women screening and contraceptive pill use), nutrition (breakfast, "
    "meals, fruit and vegetables, fried and refined foods, alcohol), psychological aspects "
    "(happiness, mood, anxiety, relaxation, relationship, work satisfaction, social life) and "
    "security (distance travelled, seat belt and helmet use, risk-taking). There may also be a "
    "blood test section: count lipids and blood pressure toward heart, and glucose, HbA1c, "
    "CRP, kidney, liver and blood count values toward medical. Values marked calculated were "
    "computed from the user's own answers and can be trusted.\n\n"

    "Your reply must begin with exactly these four lines, in this order, with nothing before "
    "them:\n"
    "BIOLOGICAL_AGE: <number>\n"
    "LIFE_EXPECTANCY: <number>\n"
    "SCORES: personal=<number>, heart=<number>, medical=<number>, nutrition=<number>, "
    "psychological=<number>, security=<number>\n"
    "HEALTH_SCORE: <number>\n\n"

    "BIOLOGICAL_AGE is a single number in years, one decimal place allowed, no units and no "
    "extra words on that line. LIFE_EXPECTANCY is a whole number of years. Each SCORES value "
    "is the net years that section added to or removed from the chronological age: negative "
    "means that section made the person biologically younger, positive means older. The six "
    "scores must sum to the difference between BIOLOGICAL_AGE and the stated chronological "
    "age. Report a score of 0 for any section the user left entirely blank.\n\n"

    "HEALTH_SCORE is a whole number from 0 to 100 rating the person's overall current health "
    "from what they provided: 85 or more means excellent, around 60 to 75 is typical for a "
    "reasonably healthy adult, below 40 means several serious concerns. It is a separate "
    "judgement from age, so a fit 70 year old can score higher than an unhealthy 30 year old. "
    "When little was provided, stay in the middle of the range and say in the explanation that "
    "the score is low confidence.\n\n"

    "Always give your best estimate even when answers are missing. If very little was "
    "provided, stay close to the stated chronological age. If no age was given, estimate from "
    "the answers alone and say so in the explanation. Never invent answers that were not "
    "given, and never treat a blank as a bad answer.\n\n"

    "If the mood answer mentions suicidal thoughts, or thinking that life is not worth the "
    "struggle, do not treat it as just another scoring input. Do not assign it a dramatic "
    "penalty in the scores or the health score, and do not dwell on it numerically. Instead, "
    "open your explanation by saying gently and briefly that this matters more than the "
    "number and is worth talking through with a doctor, a counsellor or someone they trust. "
    "Then continue with the rest of the explanation normally.\n\n"

    "After the four header lines, write a short plain-language explanation covering: which "
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

# {examples} is filled at call time, so braces inside expert text can't break the template.
template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM + "\n\n{examples}"),
    ("human", "{data}"),
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


def detect_manual(measures: dict) -> dict:
    """
    Takes the cleaned questionnaire answers and returns:
        output         the model's reply (four header lines, then the explanation)
        input_text     exactly what the model was shown, for storage
        examples_used  assessment ids of the expert-corrected cases shown to the model
    """
    if not measures:
        raise ValueError("No measures provided.")

    text = describe_answers(measures)
    examples, used = examples_for(text)

    result = model.invoke(template.invoke({"data": text, "examples": examples}))
    return {"output": as_text(result), "input_text": text, "examples_used": used}