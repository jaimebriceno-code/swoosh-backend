from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
import json
import psycopg2
import os
import time

app = FastAPI()

# === CORS CONFIG ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === OLLAMA CONFIG ===
OLLAMA_URL = "http://34.123.143.255:11434/api/generate"
OLLAMA_MODELS = ["empathetic_chicago", "ollama3"]

# === GLOBAL DB CONNECTION (initialized on startup) ===
conn = None
DATABASE_URL = os.getenv("DATABASE_URL")

# === RESEND EMAIL CONFIG ===
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
NOTIFY_EMAIL = "jbriceno@stmichaelangels.org"

# === GOOGLE MAPS CONFIG ===
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

# === EMAIL FUNCTION ===
def send_email_notification(subject, body, recipient):
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "from": "Community App <noreply@stmichaelangels.org>",
        "to": [recipient],
        "subject": subject,
        "text": body
    }
    requests.post(url, headers=headers, json=data)

# === GEOCODING FUNCTION ===
def geocode_address(address: str):
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_MAPS_KEY}
    res = requests.get(url, params=params).json()
    if res.get("status") == "OK":
        location = res["results"][0]["geometry"]["location"]
        return location["lat"], location["lng"]
    return None, None

# === FORM MODEL ===
class ServiceSubmission(BaseModel):
    service_name: str
    description: str
    location: str
    category: str
    submitter_email: str

# === STARTUP EVENT ===
@app.on_event("startup")
def startup_event():
    global conn
    retries = 5
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = True
            print("✅ Database connection established.")
            return
        except psycopg2.OperationalError as e:
            print(f"⚠️ Database connection failed (attempt {attempt+1}/{retries}): {e}")
            time.sleep(5)
    raise RuntimeError("❌ Could not connect to the database after multiple retries.")

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
        model = data.get("model", OLLAMA_MODELS[0])

        if not prompt:
            return StreamingResponse(iter(["❌ No prompt provided"]), media_type="text/plain")
        if model not in OLLAMA_MODELS:
            model = OLLAMA_MODELS[0]

        def generate():
            with requests.post(
                OLLAMA_URL,
                json={"model": model, "prompt": prompt, "stream": True},
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

# === SUBMIT NEW SERVICE ===
@app.post("/submit-service")
def submit_service(data: ServiceSubmission):
    lat, lng = geocode_address(data.location)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO pending_services (service_name, description, location, category, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data.service_name, data.description, data.location, data.category, lat, lng))

    send_email_notification(
        f"New Pending Service: {data.service_name}",
        f"Description: {data.description}\nLocation: {data.location}\nCategory: {data.category}\nLat: {lat}, Lng: {lng}",
        NOTIFY_EMAIL
    )

    thank_you_body = (
        f"Dear Friend,\n\n"
        f"Thank you for your help in expanding the visibility of vital community services.\n"
        f"Your submission to our ministry at St. Michael and All Angels will help ensure that "
        f"those in need — and those looking to help others — can find the right resources.\n\n"
        f"Your generosity and care are part of what makes our community stronger, "
        f"and I am grateful for your support in this mission.\n\n"
        f"In Christ,\n"
        f"The Rev. Jaime Briceño\n"
        f"Rector, St. Michael and All Angels Episcopal Church"
    )
    send_email_notification(
        "Thank You for Supporting Our Community Services Ministry",
        thank_you_body,
        data.submitter_email
    )

    return {"status": "pending", "message": "Service submitted for review. Thank-you email sent."}

# === APPROVE SERVICE ===
@app.post("/approve-service/{service_id}")
def approve_service(service_id: int):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT service_name, description, location, category, latitude, longitude
            FROM pending_services WHERE id=%s
        """, (service_id,))
        service = cur.fetchone()
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")

        cur.execute("""
            INSERT INTO services (service_name, description, location, category, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, service)
        cur.execute("DELETE FROM pending_services WHERE id=%s", (service_id,))

    return {"status": "approved"}
