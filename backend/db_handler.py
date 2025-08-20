import os
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pdf import extract_text_from_pdf
import re

# -----------------------
# 1. Load Resume Text
# -----------------------
resume_text = extract_text_from_pdf("ibburesume2.pdf")
print("📄 Extracted Resume Text:\n", resume_text[:300], "...\n")

# -----------------------
# 2. Improved Chunking with Overlap
# -----------------------
def chunk_text(text, chunk_size=500, overlap=100):
    # Split into sentences (basic split using ., ?, !)
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks, current_chunk = [], []

    current_length = 0
    for sentence in sentences:
        if current_length + len(sentence) <= chunk_size:
            current_chunk.append(sentence)
            current_length += len(sentence) + 1
        else:
            # save current chunk
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)

            # start new chunk with overlap
            overlap_sentences = current_chunk[-3:]  # keep last 3 sentences as overlap
            current_chunk = overlap_sentences + [sentence]
            current_length = sum(len(s) for s in current_chunk)

    # last chunk
    if current_chunk:
        chunks.append(" ".join(current_chunk).strip())

    return chunks

resume_chunks = chunk_text(resume_text, chunk_size=500, overlap=100)
print(f"✂️ Split into {len(resume_chunks)} overlapping chunks")

# -----------------------
# 3. Create Gemini Embeddings
# -----------------------
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

chunk_vectors = [embeddings.embed_query(chunk) for chunk in resume_chunks]

# -----------------------
# 4. Connect to Qdrant
# -----------------------
client = QdrantClient(host="localhost", port=6333)
collection_name = "resumes"

client.recreate_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=len(chunk_vectors[0]), distance=Distance.COSINE)
)

# -----------------------
# 5. Insert Resume Chunks
# -----------------------
points = []
for i, (chunk, vector) in enumerate(zip(resume_chunks, chunk_vectors)):
    points.append(
        PointStruct(
            id=i+1,
            vector=vector,
            payload={
                "name": "Candidate_1",
                "chunk_id": i,
                "text": chunk
            }
        )
    )

client.upsert(collection_name=collection_name, points=points)
print("✅ Resume chunks with overlap stored in Qdrant!")

# -----------------------
# 6. Query with Job Description
# -----------------------
job_description = "Looking for a backend engineer skilled in Python and FastAPI."
query_vector = embeddings.embed_query(job_description)

results = client.search(
    collection_name=collection_name,
    query_vector=query_vector,
    limit=3
)

print("\n🔍 Best Match Chunks:")
for r in results:
    print(f"Chunk ID: {r.payload['chunk_id']}, Score: {r.score:.4f}")
    print(f"Candidate: {r.payload['name']}")
    print(f"Text: {r.payload['text'][:200]}...\n")
