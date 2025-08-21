# main.py
import os
import re
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from groq import Groq

# Import your PDF extraction function (assuming it's in a file named pdf.py)
from pdf import extract_text_from_pdf

# --- 1. INITIALIZE CLIENTS (Done once when the server starts) ---
try:
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    qdrant = QdrantClient(host="localhost", port=6333)
    groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
    collection_name = "resumes"
except Exception as e:
    print(f"Error initializing clients: {e}")
    # In a real app, you might want to handle this more gracefully
    raise

app = FastAPI()

# --- 2. CONFIGURE CORS ---
# This allows your HTML/JS front end to communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# --- 3. HELPER FUNCTIONS (Your chunking logic) ---
def chunk_text(text, chunk_size=500, overlap=100):
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks, current_chunk = [], []
    current_length = 0
    for sentence in sentences:
        if current_length + len(sentence) <= chunk_size:
            current_chunk.append(sentence)
            current_length += len(sentence) + 1
        else:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
            overlap_sentences = current_chunk[-3:]
            current_chunk = overlap_sentences + [sentence]
            current_length = sum(len(s) for s in current_chunk)
    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())
    return chunks

# --- 4. API ENDPOINTS ---

@app.post("/upload-pdf")
async def upload_and_process_pdf(file: UploadFile = File(...)):
    """
    Handles uploading a resume, chunking, embedding, and storing in Qdrant.
    """
    # Save the uploaded file temporarily
    temp_file_path = f"./temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Extract and Chunk
        resume_text = extract_text_from_pdf(temp_file_path)
        resume_chunks = chunk_text(resume_text)

        # 2. Create Embeddings
        chunk_vectors = [embeddings.embed_query(chunk) for chunk in resume_chunks]

        # 3. Connect to Qdrant and Store
        qdrant.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=len(chunk_vectors[0]), distance=Distance.COSINE)
        )
        points = [
            PointStruct(
                id=i + 1,
                vector=vector,
                payload={"name": "Candidate_1", "chunk_id": i, "text": chunk}
            )
            for i, (chunk, vector) in enumerate(zip(resume_chunks, chunk_vectors))
        ]
        qdrant.upsert(collection_name=collection_name, points=points)

        return {"message": "Resume processed and stored successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.post("/analyze")
async def analyze_job_description(job_description: str = Form(...)):
    """
    Analyzes the job description against the stored resume.
    """
    try:
        # 1. Embed Job Description and Search Qdrant
        query_vector = embeddings.embed_query(job_description)
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=5  # Retrieve a few more chunks for better context
        )
        retrieved_chunks = [r.payload["text"] for r in results]
        
        # 2. Build Prompt and Query Groq
        prompt = f"""
        Analyze the following resume chunks in the context of the job description.
        
        Job Description: {job_description}
        
        Resume Chunks:
        {retrieved_chunks}
        
        Based on the job description, provide a score from 0 to 100 for the candidate's match.
        Then, list skills or experiences from the resume that are a good match.
        Finally, list key skills from the job description that seem to be missing from the resume.

        Provide the output in the following format, and nothing else:
        SCORE: [score]
        MATCHES: [comma-separated list of matching skills]
        MISSING: [comma-separated list of missing skills]
        """

        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a helpful hiring assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        analysis_text = response.choices[0].message.content

        # 3. Parse the LLM's response
        score = re.search(r"SCORE: (\d+)", analysis_text)
        matches = re.search(r"MATCHES: (.*)", analysis_text)
        missing = re.search(r"MISSING: (.*)", analysis_text)

        return {
            "score": int(score.group(1)) if score else 0,
            "matches": [m.strip() for m in matches.group(1).split(',')] if matches else [],
            "missing": [m.strip() for m in missing.group(1).split(',')] if missing else [],
            "raw_analysis": analysis_text # Also send the raw text for debugging
        }
    except Exception as e:
        # Check if collection exists
        try:
             qdrant.get_collection(collection_name=collection_name)
        except Exception:
             raise HTTPException(status_code=400, detail="No resume has been uploaded yet. Please upload a PDF first.")
        raise HTTPException(status_code=500, detail=f"An error occurred during analysis: {e}")