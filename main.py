from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# === CORS CONFIG ===
# Wide-open for testing — switch to your Builder.io domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CONFIG ===
OLLAMA_URL = "http://34.123.143.255:11434/api/generate"  # VM Ollama endpoint
OLLAMA_MODEL = "empathetic_chicago"  # Your custom model

# === TEST ROUTE ===
@app.get("/")
def root():
    return {"message": "FastAPI backend is running"}

# === ASK ENDPOINT ===
@app.post("/ask")
async def ask(request: Request):
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return {"response": "❌ No prompt provided"}

        # Send prompt to Ollama
        ollama_response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt
            }
        )

        if ollama_response.status_code != 200:
            return {"response": f"Error from Ollama: {ollama_response.text}"}

        ollama_json = ollama_response.json()
        ollama_text = ollama_json.get("response", "").strip()

        return {"response": ollama_text}

    except Exception as e:
        return {"response": f"⚠️ Error processing request: {str(e)}"}
