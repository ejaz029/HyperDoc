from langchain_groq import ChatGroq

from app.config import settings


llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=settings.groq_api_key,
    temperature=0,
)