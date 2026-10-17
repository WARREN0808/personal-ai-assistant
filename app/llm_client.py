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


def generate_tasks(goal_title: str, deadline=None) -> list[str]:
    deadline_str = f", à atteindre avant le {deadline.strftime('%d/%m/%Y')}" if deadline else ""
    prompt = (
        f"Je veux atteindre l'objectif suivant{deadline_str} : {goal_title}\n"
        f"Propose-moi exactement 5 tâches concrètes pour y arriver.\n"
        f"Réponds uniquement avec une tâche par ligne, numérotée. Rien d'autre."
    )

    contents = [{"role": "user", "parts": [{"text": prompt}]}]

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(model=MODEL, contents=contents)
            lines = response.text.strip().split("\n")
            tasks = []
            for line in lines:
                line = line.strip()
                if line:
                    if line[0].isdigit():
                        line = line.split(".", 1)[-1].split(")", 1)[-1].strip()
                    tasks.append(line)
            return tasks
        except errors.ServerError:
            if attempt == MAX_ATTEMPTS - 1:
                raise
            time.sleep(2 * (attempt + 1))
