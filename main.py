from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
import json
import psycopg2
import os

app = FastAPI()

# === CORS CONFIG ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === CONFIG ===
OLLAMA_URL = "http://34.123.143.255:11434/api/generate"  # VM Ollama endpoint
OLLAMA_MODEL = "empathetic_chicago"

# === DATABASE CONFIG ===
conn = psycopg2.connect(
    dbname="community_db_s5t2",
    user="community_db_s5t2_user",
    password="2icMmLn8kmn0ZMob9XILHg9UKWIei1GB",
    host="dpg-d24hk03e5dus73ac32og-a.ohio-postgres.render.com",
    port="5432"
)

# === RESEND EMAIL CONFIG ===
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "re_S3Xe3Wce_PxkComorKYxGYfvaxgk2b9TD")
NOTIFY_EMAIL = "jbriceno@stmichaelangels.org"  # change this

# === EMAIL FUNCTION ===
def send_email_notification(subject, body):
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": "Community App <noreply@yourdomain.com>",
        "to": [NOTIFY_EMAIL],
        "subject": subject,
        "text": body
    }
    res = requests.post(url, headers=headers, json=data)
    return res.status_code, res.text

# === FORM MODEL ===
class ServiceSubmission(BaseModel):
    service_name: str
    description: str
    location: str
    category: str

# === ROOT TEST ===
@app.get("/")
def root():
    return {"message": "FastAPI backend is running"}

# === OLLAMA STREAMING ENDPOINT ===
@app.post("/ask")
async def ask(request: Request):
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

# === SUBMIT NEW SERVICE (PENDING) ===
@app.post("/submit-service")
def submit_service(data: ServiceSubmission):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO pending_services (service_name, description, location, category)
            VALUES (%s, %s, %s, %s)
        """, (data.service_name, data.description, data.location, data.category))
        conn.commit()

    # Send notification email
    subject = f"New Pending Service: {data.service_name}"
    body = f"Description: {data.description}\nLocation: {data.location}\nCategory: {data.category}"
    send_email_notification(subject, body)

    return {"status": "pending", "message": "Service submitted for review."}

# === APPROVE SERVICE ===
@app.post("/approve-service/{service_id}")
def approve_service(service_id: int):
    with conn.cursor() as cur:
        cur.execute("SELECT service_name, description, location, category FROM pending_services WHERE id=%s", (service_id,))
        service = cur.fetchone()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        cur.execute("""
            INSERT INTO services (service_name, description, location, category)
            VALUES (%s, %s, %s, %s)
        """, service)
        cur.execute("DELETE FROM pending_services WHERE id=%s", (service_id,))
        conn.commit()

    return {"status": "approved"}
