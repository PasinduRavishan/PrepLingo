"""
langchain_layer/vector_store/store_manager.py

WHAT IS A VECTOR STORE?
  A vector store is a specialized database that stores text as "vectors"
  (arrays of numbers that capture the MEANING of text, not just the words).

  When you search, it doesn't look for exact keyword matches.
  It looks for text with SIMILAR MEANING to your query.

  Example:
    Query: "How does a cache work?"
    Keyword search: finds only docs with "cache"
    Vector search: finds docs about "Redis", "memoization", "CDN" too
                   because they all have similar meaning/context

HOW ChromaDB FITS IN:
  ChromaDB is our vector database. It stores:
  ┌──────────────────────────────────────────┐
  │  Text: "Database indexing creates a B-   │
  │         tree structure that..."           │
  │  Vector: [0.23, -0.51, 0.89, ...]        │
  │           (768 numbers representing meaning)│
  │  Metadata: {interview_type: "technical", │
  │             topic: "databases",           │
  │             source: "technical/databases.md"} │
  └──────────────────────────────────────────┘

  The metadata is KEY — it lets us filter:
  "Only give me chunks tagged as interview_type=technical"
  This prevents system_design knowledge from showing up in a behavioral interview.

TWO COLLECTIONS:
  "knowledge"  → static domain documents (ingested once from knowledge_base/)
  "resumes"    → user resume chunks (added when each user uploads their PDF)
"""

from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import get_settings

settings = get_settings()

# The embedding model — converts text to vectors
# gemini-embedding-001 is Google's current embedding model, free with your API key
# Replaces deprecated text-embedding-004
# NOTE: if you change this, delete vector_store_data/ and re-run ingest_knowledge.py
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.embedding_model,
    google_api_key=settings.google_api_key,
)


def get_knowledge_store() -> Chroma:
    """
    Returns the ChromaDB collection for domain knowledge.
    
    This is populated ONCE by running: python scripts/ingest_knowledge.py
    It contains all the .md files from knowledge_base/
    
    persist_directory: where ChromaDB saves its data on disk
    collection_name: think of this as a "table name" in ChromaDB
    """
    return Chroma(
        collection_name="knowledge",
        embedding_function=embeddings,
        persist_directory=settings.vector_store_path,
    )


def get_resume_store() -> Chroma:
    """
    Returns the ChromaDB collection for user resume chunks.
    
    This grows as users upload resumes.
    Resume chunks are filtered by user_id in metadata when retrieving.
    """
    return Chroma(
        collection_name="resumes",
        embedding_function=embeddings,
        persist_directory=settings.vector_store_path,
    )


def get_knowledge_retriever(interview_type: str, k: int = 3):
    """
    Creates a retriever filtered to a specific interview type.
    
    A Retriever wraps the vector store and provides a simple interface:
        retriever.invoke("my query") → [list of relevant Document objects]
    
    The filter ensures we only get chunks relevant to THIS interview type.
    Without it, a technical interview question might pull behavioral docs.
    
    Args:
        interview_type: "technical", "system_design", "behavioral", "resume"
        k: number of chunks to retrieve (top-k most similar)
    """
    store = get_knowledge_store()
    return store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k,
            "filter": {"interview_type": interview_type},  # ChromaDB metadata filter
        },
    )


def get_resume_retriever(guest_id: str, k: int = 2):
    """
    Creates a retriever filtered to a specific user's resume.
    
    Args:
        guest_id: The user's UUID — filters to their resume chunks only
        k: number of resume chunks to retrieve
    """
    store = get_resume_store()
    return store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": k,
            "filter": {"guest_id": guest_id},  # Only this user's resume
        },
    )
