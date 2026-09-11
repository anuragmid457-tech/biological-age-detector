from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate


SYSTEM = (
    "You estimate biological age from health, lifestyle and biomarker details that a user "
    "entered manually.\n\n"
    "Your reply must begin with exactly this line and nothing before it:\n"
    "BIOLOGICAL_AGE: <number>\n"
    "Use a single number in years, one decimal place allowed, no units and no extra words on "
    "that line. Always give your best estimate even when some values are missing; if very "
    "little was provided, stay close to the stated chronological age.\n\n"
    "After that line, write a short plain-language explanation covering: which values pushed "
    "the estimate up or down, anything missing or outside a plausible human range, and one or "
    "two things that would most improve the number. Never invent values that were not given.\n\n"
    "Formatting rules for that explanation, follow them strictly:\n"
    "Write plain text only. Do not use asterisks, hashes, underscores, backticks, hyphens or "
    "any other markdown or bullet symbols anywhere. Do not write headings. Use ordinary "
    "sentences grouped into short paragraphs, separated by a blank line. If you need to list "
    "several items, write them as a sentence separated by commas, not as a list.\n\n"
    "You are not a doctor. Do not diagnose and do not give treatment plans."
)

template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "{data}")
])

model = init_chat_model("gemini-3.1-flash-lite-preview", model_provider="google_genai")


def detect_manual(measures: dict) -> str:
    """
    Takes manually entered biological details and returns a string whose first line is
    'BIOLOGICAL_AGE: <number>', followed by a plain-text explanation.
    """
    if not measures:
        raise ValueError("No measures provided.")

    text = "\n".join(f"{key}: {value}" for key, value in measures.items())

    prompt = template.invoke({"data": text})
    result = model.invoke(prompt)
    return result.text()