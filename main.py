from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

# Allow your Builder.io environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://25a4a46a8ed34411919d4d671bde7717-main.projects.builder.my"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Replace with your LocalAI VM's IP
LOCALAI_URL = "http://34.123.143.255:8080/v1/chat/completions"

@app.post("/chat")
async def chat(request: Request):
    payload = await request.json()
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(LOCALAI_URL, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        return {"error": f"Request error: {str(e)}"}
    except httpx.HTTPStatusError as e:
        return {"error": f"LocalAI responded with {e.response.status_code}"}
