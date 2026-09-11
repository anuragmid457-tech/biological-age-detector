from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.chat_models import init_chat_model


SYSTEM = (
    "You estimate biological age from a medical or lab document. Use only the health, "
    "lifestyle and biomarker details in the text. Ignore headers, page numbers, addresses "
    "and other irrelevant content.\n\n"
    "Your reply must begin with exactly this line and nothing before it:\n"
    "BIOLOGICAL_AGE: <number>\n"
    "Use a single number in years, one decimal place allowed, no units and no extra words on "
    "that line. Always give your best estimate even when some values are missing; if very "
    "little is present, stay close to any stated chronological age.\n\n"
    "After that line, write a short plain-language explanation covering: which values pushed "
    "the estimate up or down, anything missing or outside a plausible human range, and one or "
    "two things that would most improve the number. Never invent values that are not in the "
    "document.\n\n"
    "Formatting rules for that explanation, follow them strictly:\n"
    "Write plain text only. Do not use asterisks, hashes, underscores, backticks, hyphens or "
    "any other markdown or bullet symbols anywhere. Do not write headings. Use ordinary "
    "sentences grouped into short paragraphs, separated by a blank line. If you need to list "
    "several items, write them as a sentence separated by commas, not as a list.\n\n"
    "You are not a doctor. Do not diagnose and do not give treatment plans."
)

template = ChatPromptTemplate.from_messages([
    ("system", SYSTEM),
    ("human", "{pdf}")
])

model = init_chat_model("gemini-3.1-flash-lite-preview", model_provider="google_genai")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

QUERIES = [
    "biomarkers, blood test results, lab values",
    "lifestyle habits, diet, exercise, sleep",
    "medical history, conditions, medications",
    "age, weight, height, vital signs",
]


def detect(path,age=None):
    docs = PyPDFLoader(path).load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    vectorstore = Chroma.from_documents(documents=chunks, embedding=embeddings)
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
        if age:
            text = f"The person states their chronological age is {age}.\n\n{text}"
        

    result = model.invoke(template.invoke({"pdf": text}))
    return result.text()