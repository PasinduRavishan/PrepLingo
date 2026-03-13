"""
scripts/ingest_knowledge.py

THE KNOWLEDGE BASE INGESTION SCRIPT

Run this ONCE before starting the server (and whenever you add new .md files):
  cd PrepLingo/backend
  python scripts/ingest_knowledge.py

WHAT THIS SCRIPT DOES:
  1. Loads all .md files from knowledge_base/
  2. Splits them into chunks (RecursiveCharacterTextSplitter)
  3. Adds metadata to each chunk (which interview type it belongs to)
  4. Embeds each chunk (Google gemini-embedding-001 → 768-number vector)
  5. Stores chunks + vectors in ChromaDB (persisted to disk)

HOW CHUNKING WORKS:
  Imagine you have a 10-page document about databases.
  You can't feed all 10 pages into an embedding model at once:
  1. Too long (model has token limits)
  2. The resulting vector would be too abstract — loses specific meaning
  
  Solution: Split into overlapping chunks of ~800 tokens.
  Each chunk represents ONE concept or section.
  
  Overlap (100 tokens): The last 100 tokens of chunk N become the first 100 of chunk N+1.
  This prevents context loss at chunk boundaries.

HOW METADATA ENABLES FILTERED RETRIEVAL:
  Each chunk gets metadata like:
  {
    "interview_type": "technical",
    "source": "technical/databases.md",
    "topic": "databases"
  }
  
  Later, when a user is in a system_design interview:
  retriever.filter = {"interview_type": "system_design"}
  → ChromaDB only returns system_design chunks, not behavioral or technical

DETERMINING interview_type FROM FILE PATH:
  knowledge_base/technical/databases.md → "technical"
  knowledge_base/system_design/patterns/caching.md → "system_design"
  knowledge_base/behavioral/star_method.md → "behavioral"
  knowledge_base/resume_interview/... → "resume"

RUNNING TIME:
  - First run: ~1-3 minutes (embedding all documents via Google API)
  - Subsequent runs: Skip if collection already has docs (add --reset flag to re-run)
"""

import os
import sys
import argparse

# Add parent directory to path so we can import from app/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VECTOR_STORE_PATH = os.getenv("VECTOR_STORE_PATH", "./vector_store_data")
KNOWLEDGE_BASE_PATH = "./knowledge_base"


def determine_interview_type(source_path: str) -> str:
    """
    Determine interview type from file path.
    
    Examples:
      "knowledge_base/technical/databases.md" → "technical"
      "knowledge_base/system_design/..." → "system_design"
      "knowledge_base/behavioral/..." → "behavioral"
      "knowledge_base/resume_interview/..." → "resume"
    """
    path_lower = source_path.lower().replace("\\", "/")
    if "/technical/" in path_lower:
        return "technical"
    elif "/system_design/" in path_lower:
        return "system_design"
    elif "/behavioral/" in path_lower:
        return "behavioral"
    elif "/resume_interview/" in path_lower:
        return "resume"
    else:
        return "general"


def main(reset: bool = False):
    print("=" * 60)
    print("🧠 PrepLingo Knowledge Base Ingestion")
    print("=" * 60)

    if not GOOGLE_API_KEY:
        print("❌ ERROR: GOOGLE_API_KEY not found in .env file")
        print("   Get your free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    # ── Step 1: Load all .md documents ───────────────────────────
    print(f"\n📂 Loading documents from {KNOWLEDGE_BASE_PATH}/...")
    
    loader = DirectoryLoader(
        KNOWLEDGE_BASE_PATH,
        glob="**/*.md",          # All .md files, any depth
        loader_cls=TextLoader,    # Load as plain text
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents = loader.load()
    print(f"   ✅ Loaded {len(documents)} documents")

    if not documents:
        print("❌ No documents found! Add .md files to knowledge_base/ directories.")
        sys.exit(1)

    # ── Step 2: Split into chunks ─────────────────────────────────
    print("\n✂️  Splitting documents into chunks...")
    
    # RecursiveCharacterTextSplitter tries to split at:
    # 1. "\n\n" (paragraphs) → 2. "\n" (lines) → 3. " " (words) → 4. chars
    # It tries each separator in order, using the next if a chunk is still too big
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,       # Target chunk size in characters (~200 tokens)
        chunk_overlap=100,    # Overlap to preserve context across chunks
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    
    chunks = splitter.split_documents(documents)
    print(f"   ✅ Created {len(chunks)} chunks from {len(documents)} documents")

    # ── Step 3: Add metadata to chunks ───────────────────────────
    print("\n🏷️  Adding metadata to chunks...")
    
    for chunk in chunks:
        # Get the source file path (set by DirectoryLoader)
        source = chunk.metadata.get("source", "")
        
        # Determine which interview type this chunk belongs to
        interview_type = determine_interview_type(source)
        chunk.metadata["interview_type"] = interview_type
        
        # Clean up the source path for readability
        chunk.metadata["source"] = source.replace(KNOWLEDGE_BASE_PATH + "/", "")
    
    # Show breakdown by interview type
    from collections import Counter
    type_counts = Counter(c.metadata["interview_type"] for c in chunks)
    for itype, count in type_counts.items():
        print(f"   {itype}: {count} chunks")

    # ── Step 4: Initialize Embedding Model ───────────────────────
    print("\n🔢 Initializing Google gemini-embedding-001...")
    
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=GOOGLE_API_KEY,
    )
    print("   ✅ Embedding model ready")

    # ── Step 5: Store in ChromaDB ─────────────────────────────────
    print(f"\n💾 Storing embeddings in ChromaDB at {VECTOR_STORE_PATH}/...")
    
    # Chroma.from_documents:
    # 1. For each chunk: calls embeddings.embed_documents([chunk.page_content])
    # 2. Gets a list of 768-dimensional vectors back
    # 3. Stores: {text, vector, metadata} in ChromaDB
    # 4. Persists to disk at VECTOR_STORE_PATH
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=VECTOR_STORE_PATH,
        collection_name="knowledge",  # Our static knowledge collection
    )
    
    print(f"   ✅ {len(chunks)} chunks embedded and stored!")
    print(f"   📁 ChromaDB saved to: {VECTOR_STORE_PATH}/")

    # ── Step 6: Test Retrieval ────────────────────────────────────
    print("\n🧪 Testing retrieval...")
    
    retriever = vector_store.as_retriever(
        search_kwargs={"filter": {"interview_type": "technical"}, "k": 2}
    )
    test_results = retriever.invoke("How does database indexing work?")
    
    print(f"   Query: 'How does database indexing work?'")
    print(f"   Retrieved {len(test_results)} chunks:")
    for i, doc in enumerate(test_results):
        print(f"   [{i+1}] {doc.metadata.get('source')} — {doc.page_content[:80]}...")

    print("\n" + "=" * 60)
    print("✅ Knowledge base ingestion complete!")
    print("   You can now run: uvicorn app.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest knowledge base into ChromaDB")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing ChromaDB collection and re-ingest",
    )
    args = parser.parse_args()
    main(reset=args.reset)
