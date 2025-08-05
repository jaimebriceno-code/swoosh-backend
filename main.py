from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

@app.get("/")
def root():
    return {"message": "CORS open for all origins"}

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

