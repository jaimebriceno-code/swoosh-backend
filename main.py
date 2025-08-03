from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests

app = FastAPI()


class ChatRequest(BaseModel):
    prompt: str


@app.get("/")
def read_root():
    return {"message": "Swoosh Backend is running on the VM and connected to Ollama!"}


@app.post("/chat")
def chat_with_ollama(request: ChatRequest):
    ollama_url = "http://localhost:11434/api/chat"

    try:
        response = requests.post(
            ollama_url,
            json={
                "model": "llama3",
                "messages": [
                    {"role": "user", "content": request.prompt}
                ]
            }
        )

        response.raise_for_status()
        data = response.json()
        return {
            "response": data.get("message", {}).get("content", ""),
            "full": data
        }

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}
