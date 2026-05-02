import os
from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"{name} not found in .env file")
    return value


class Settings:
    GOOGLE_API_KEY: str = _required("GOOGLE_API_KEY")
    GEMINI_CHAT_MODEL: str = _required("GEMINI_CHAT_MODEL")
    GEMINI_EMBED_MODEL: str = _required("GEMINI_EMBED_MODEL")
    CHROMA_DIR: str = _required("CHROMA_DIR")


settings = Settings()
