from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI()

OLLAMA_URL = "http://localhost:11434/api/chat"

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

@app.post("/chat")
def chat_with_ollama(request: ChatRequest):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "llama3",
                "messages": [msg.dict() for msg in request.messages]
            }
        )
        response.raise_for_status()
        return response.json()["message"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
