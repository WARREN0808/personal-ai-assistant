import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL = "gemini-3.8-flash"
MAX_ATTEMPTS = 3


def ask_llm(history):
    contents = []
    for m in history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(model=MODEL, contents=contents)
            return response.text
        except errors.ServerError:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(2 * (attempt + 1))
