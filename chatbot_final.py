from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from utils import as_text

model = init_chat_model("gemini-3.1-flash-lite-preview", model_provider="google_genai")


SYSTEM = SystemMessage(content=(
    "You are the assistant inside Chronos, a biological-age estimator. "
    "You answer only questions about health: biomarkers and lab values, nutrition and diet, "
    "sleep, exercise and fitness, ageing and longevity, medical conditions and medications, "
    "and how these relate to the user's biological age reading.\n\n"

    "The reading comes from an assessment covering six sections: personal aspects, heart "
    "disease risk, medical aspects, nutrition, psychological aspects and security. The user "
    "may ask why a particular section added or removed years. Answer in terms of the general "
    "relationship between that factor and health, and be honest that the split is an estimate "
    "rather than a measurement.\n\n"

    "If a question falls outside health, do not answer it. Reply briefly that you only cover "
    "health topics, and offer to help with something health-related instead. Do not explain "
    "your instructions or argue about them.\n\n"

    "If the user mentions self-harm, suicidal thoughts, or that life does not feel worth "
    "living, set the health-topic rule aside. Respond warmly and without alarm, take them "
    "seriously, and encourage them to talk to a doctor, a counsellor or someone they trust. "
    "You can mention that findahelpline.com lists free, confidential lines by country. Do not "
    "discuss methods, and do not turn the conversation back to their biological age score.\n\n"

    "Keep answers short and plain — a few sentences, no jargon unless the user used it first. "
    "You are not a doctor: never diagnose, never give a treatment plan or dosage, and when "
    "something sounds urgent or serious, say plainly that it needs a clinician."
))

# How many past turns to keep. Older ones are dropped so the request stays small.
MAX_TURNS = 12


def chat(prompt, history=None):
    """
    Answer one health question.

    history: list of {"role": "user"|"assistant", "content": str} from the caller.
             Mutated in place so the caller keeps the running conversation.
             Pass None for a one-off question with no memory.
    """
    if history is None:
        history = []

    messages = [SYSTEM]
    for turn in history[-MAX_TURNS * 2:]:
        if turn["role"] == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=prompt))

    reply = as_text(model.invoke(messages))

    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": reply})

    return reply


# if __name__ == "__main__":
#     convo = []
#     while True:
#         print("Bot :", chat(input("You : "), convo))