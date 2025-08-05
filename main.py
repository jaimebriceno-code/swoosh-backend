from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import requests
import json

app = FastAPI()

# === CORS CONFIG ===
# Wide-open for testing — restrict to Builder.io domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CONFIG ===
OLLAMA_URL = "http://34.123.143.255:11434/api/generate"
OLLAMA_MODEL = "empathetic_chicago"

# === TEST ROUTE ===
@app.get("/")
def root():
    return {"message": "FastAPI backend is running"}

# === STREAMING ASK ENDPOINT ===
@app.post("/ask")
async def ask(request: Request):
    """
    Streams tokens from Ollama to the frontend as they are generated.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            return StreamingResponse(iter(["❌ No prompt provided"]), media_type="text/plain")

        def generate():
            with requests.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            ) as r:
                for line in r.iter_lines():
                    if line:
                        try:
                            payload = json.loads(line.decode("utf-8"))
                            chunk = payload.get("response", "")
                            if chunk:
                                yield chunk
                        except json.JSONDecodeError:
                            pass

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        return StreamingResponse(iter([f"⚠️ Error: {str(e)}"]), media_type="text/plain")
