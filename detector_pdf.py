from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain.chat_models import init_chat_model
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

from learning import embeddings, examples_for
from utils import as_text


SYSTEM = (
    "You estimate biological age from a medical or lab document. Use only the health, "
    "lifestyle and biomarker details in the text. Ignore headers, page numbers, addresses "
    "and other irrelevant content.\n\n"

    "Your reply must begin with exactly these four lines, in this order, with nothing before "
    "them:\n"
    "BIOLOGICAL_AGE: <number>\n"
    "LIFE_EXPECTANCY: <number>\n"
    "SCORES: personal=<number>, heart=<number>, medical=<number>, nutrition=<number>, "
    "psychological=<number>, security=<number>\n"
    "HEALTH_SCORE: <number>\n\n"

    "BIOLOGICAL_AGE is a single number in years, one decimal place allowed, no units and no "
    "extra words on that line. LIFE_EXPECTANCY is a whole number of years. Each SCORES value "
    "is the net years that area added to or removed from the chronological age: negative means "
    "biologically younger, positive means older. Group what you find in the document into "
    "those six areas: personal covers age, gender, family longevity and sleep; heart covers "
    "cholesterol, blood pressure, smoking, weight distribution, stress and physical activity; "
    "medical covers screening history, cardiac, respiratory, digestive, diabetic, kidney, "
    "liver, blood count, inflammation and medication findings; nutrition covers diet and "
    "alcohol; psychological covers mood, anxiety and social factors; security covers driving "
    "and risk exposure. Report 0 for any area the document says nothing about, which is "
    "common for lab reports.\n\n"

    "HEALTH_SCORE is a whole number from 0 to 100 rating the person's overall current health "
    "from what the document shows: 85 or more means excellent, around 60 to 75 is typical for "
    "a reasonably healthy adult, below 40 means several serious concerns. It is a separate "
    "judgement from age. A lab report shows only part of the picture, so when it covers little, "
    "stay in the middle of the range and say the score is low confidence.\n\n"

    "If the text begins with a line reading 'Stated chronological age', that value came "
    "directly from the user and is authoritative. Anchor your estimate to it, make the six "
    "scores sum to the difference between your estimate and that age, and mention in your "
    "explanation how far above or below it the estimate lands.\n\n"

    "Always give your best estimate even when some values are missing. If very little is "
    "present, stay close to any stated chronological age.\n\n"

    "After the four header lines, write a short plain-language explanation covering: which "
    "values pushed the estimate up or down, anything missing or outside a plausible human "
    "range, and one or two things that would most improve the number. Never invent values "
    "that are not in the document.\n\n"

    "Formatting rules for that explanation, follow them strictly:\n"
    "Write plain text only. Do not use asterisks, hashes, underscores, backticks, hyphens or "
    "any other markdown or bullet symbols anywhere. Do not write headings. Use ordinary "
    "sentences grouped into short paragraphs, separated by a blank line. If you need to list "
    "several items, write them as a sentence separated by commas, not as a list.\n\n"

    "You are not a doctor. Do not diagnose and do not give treatment plans. Where a value "
    "looks urgent, say plainly that it needs a clinician."
)

template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM + "\n\n{examples}"),
    ("human", "{pdf}"),
])

model = init_chat_model("gemini-3.1-flash-lite-preview", model_provider="google_genai")

QUERIES = [
    "biomarkers, blood test results, lab values",
    "lifestyle habits, diet, exercise, sleep",
    "medical history, conditions, medications",
    "age, weight, height, vital signs",
    "mood, stress, anxiety, mental health",
    "smoking, alcohol, substance use",
]


def detect(path, age=None) -> dict:
    """
    Returns:
        output         the model's reply (four header lines, then the explanation)
        input_text     exactly what the model was shown, for storage
        examples_used  assessment ids of the expert-corrected cases shown to the model
    """
    docs = PyPDFLoader(path).load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # A fresh store per request. The previous Chroma.from_documents() call wrote every
    # upload into one shared in-process collection, so later users' retrieval could pull
    # passages from earlier users' PDFs.
    text = ""
    if chunks:
        vectorstore = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        seen = set()
        relevant = []
        for q in QUERIES:
            for doc in retriever.invoke(q):
                if doc.page_content not in seen:
                    seen.add(doc.page_content)
                    relevant.append(doc)

        # Send only the retrieved passages, not the whole document.
        text = "\n\n".join(d.page_content for d in relevant)

    if not text.strip():
        text = "\n\n".join(d.page_content for d in docs)

    if age is not None:
        text = f"Stated chronological age: {age}\n\n{text}"

    examples, used = examples_for(text)

    result = model.invoke(template.invoke({"pdf": text, "examples": examples}))
    return {"output": as_text(result), "input_text": text, "examples_used": used}