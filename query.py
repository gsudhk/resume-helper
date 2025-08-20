import os
import pkg_resources
from qdrant_client import QdrantClient
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from groq import Groq


# -----------------------
# 1. Setup Clients
# -----------------------
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

qdrant = QdrantClient(host="localhost", port=6333)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

collection_name = "resumes"


# -----------------------
# 2. Check Qdrant Version
# -----------------------
def is_new_qdrant():
    try:
        version = pkg_resources.get_distribution("qdrant-client").version
        major, minor, *_ = map(int, version.split("."))
        return (major, minor) >= (1, 9)
    except Exception:
        return False


USE_NEW_API = is_new_qdrant()


# -----------------------
# 3. Query Function
# -----------------------
def query_resume(job_description: str, top_k=3):
    # Convert job description to embedding
    query_vector = embeddings.embed_query(job_description)

    # Search in Qdrant
    if USE_NEW_API:
        # For Qdrant >= 1.9, use the new search API
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
        )
    else:
        # For older Qdrant versions, use the legacy search API
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k
        )

    # Collect retrieved chunks
    retrieved_chunks = [r.payload["text"] for r in results]

    # Build prompt for Groq
    prompt = f"""
    Job Description: {job_description}

    Retrieved Resume Chunks:
    {retrieved_chunks}

    Based on the job description, analyze how well the candidate matches and give a score out of 100.
    Also suggest:
    - Skills to be added
    - Skills to be removed
    """

    # Ask Groq for reasoning
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Groq model
        messages=[
            {"role": "system", "content": "You are a hiring assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    return results, response.choices[0].message.content


# -----------------------
# 4. Example Usage
# -----------------------
if __name__ == "__main__":
    while True:
        job_desc = input("📝 Enter job description (or 'exit' to quit): ")
        if job_desc.lower() == "exit":
            break

        results, groq_summary = query_resume(job_desc)

        print("\n🔍 Best Matching Resume Chunks:\n")
        for r in results:
            print(f"📌 Candidate: {r.payload.get('name', 'Unknown')}")
            print(f"   Chunk ID: {r.payload.get('chunk_id', 'N/A')}")
            print(f"   Score: {getattr(r, 'score', 0):.4f}")
            print(f"   Text: {r.payload['text'][:200]}...\n")

        print("🤖 Groq Analysis:\n", groq_summary, "\n")
