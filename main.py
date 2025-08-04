from fastapi import FastAPI
from pydantic import BaseModel
import requests

app = FastAPI()

class PromptRequest(BaseModel):
    prompt: str

@app.post("/ask")
def ask_ollama(req: PromptRequest):
    try:
        response = requests.post(
            "http://34.123.143.255:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": req.prompt,
                "stream": False
            },
            timeout=60
        )
        data = response.json()
        return {"response": data.get("response", "No reply")}
    except Exception as e:
        return {"error": str(e)}
