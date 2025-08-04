from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

# ✅ Add your Builder.io preview site here
origins = [
    "https://25a4a46a8ed34411919d4d671bde7717-main.projects.builder.my",
    "https://builder.io",
    "http://localhost:3000"  # optional for local dev
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

