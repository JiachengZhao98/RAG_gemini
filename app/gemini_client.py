from google import genai
from app.config import settings

def get_client():
    # get google genai client
    return genai.Client(api_key=settings.GOOGLE_API_KEY)
