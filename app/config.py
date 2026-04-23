import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL")
    GEMINI_EMBED_MODEL = os.getenv("GEMINI_EMBED_MODEL")
    CHROMA_DIR = os.getenv("CHROMA_DIR")

settings = Settings()

if not settings.GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env file")

if not settings.GEMINI_CHAT_MODEL:
    raise ValueError("GEMINI_CHAT_MODEL not found in .env file")

if not settings.GEMINI_EMBED_MODEL:
    raise ValueError("GEMINI_EMBED_MODEL not found in .env file")

if not settings.CHROMA_DIR:
    raise ValueError("CHROMA_DIR not found in .env file")

