from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

app = FastAPI()

# Allow all origins for testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)) -> Dict[str, str]:
    # Just a test response for now
    return {"message": "✅ Resume uploaded and processed successfully!"}

@app.post("/analyze")
async def analyze(job_description: str = Form(...)) -> Dict[str, list]:
    # Dummy data to test frontend
    return {
        "matches": ["python", "fastapi", "ai"],
        "additions": ["docker", "kubernetes"],
        "deletions": ["old-tech"]
    }
