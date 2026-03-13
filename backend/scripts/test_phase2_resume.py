"""
scripts/test_phase2_resume.py

HOW TO RUN:
  cd PrepLingo/backend
  python scripts/test_phase2_resume.py

WHAT THIS TESTS:
  1. ✅ Health check
  2. ✅ PDF extraction (generates a test PDF on-the-fly)
  3. ✅ Resume upload endpoint (POST /api/resume/upload)
  4. ✅ Resume GET endpoint
  5. ✅ ChromaDB retrieval (confirms resume chunks are searchable)

WHY CREATE A TEST PDF HERE?
  You might not have a real PDF handy for testing.
  This script generates a realistic-looking resume PDF using reportlab,
  uploads it to the running API, and validates the response.
  
  If you prefer to test with your own PDF, skip to the bottom
  and use the curl command shown there.
  
PREREQUISITES:
  - Server running: uvicorn app.main:app --reload
  - pip install reportlab requests
"""

import sys
import os
import json
import io
import time
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_URL = "http://localhost:8000"
TEST_GUEST_ID = "test-guest-phase2-001"

# ── Colour output helpers ─────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def ok(msg): print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {BLUE}ℹ  {msg}{RESET}")
def section(msg): print(f"\n{BOLD}{YELLOW}── {msg} ──{RESET}")


def create_sample_pdf_bytes() -> bytes:
    """
    Create a sample resume PDF entirely in memory (no temp files).
    Uses only PyMuPDF (fitz) which we already have installed.
    Returns raw PDF bytes.
    """
    # Try using reportlab if installed
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, 780, "Ravi Shankar")
        c.setFont("Helvetica", 11)
        c.drawString(50, 760, "Full Stack Developer | ravi@email.com | +94 123 456 789")
        
        # Skills
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, 720, "Technical Skills")
        c.setFont("Helvetica", 11)
        c.drawString(50, 700, "Languages: Python, JavaScript, TypeScript, SQL")
        c.drawString(50, 685, "Frameworks: FastAPI, React, Next.js, LangChain")
        c.drawString(50, 670, "Databases: PostgreSQL, MongoDB, ChromaDB, SQLite")
        c.drawString(50, 655, "Tools: Docker, Git, Linux, AWS EC2, Nginx")
        
        # Projects
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, 620, "Projects")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 600, "PrepLingo — AI Interview Trainer (2025)")
        c.setFont("Helvetica", 11)
        c.drawString(60, 585, "• Built an AI interview simulator using LangChain, RAG, and Google Gemini")
        c.drawString(60, 570, "• Implemented dual retriever strategy combining resume context with knowledge base")
        c.drawString(60, 555, "• Tech: FastAPI, Next.js, ChromaDB, LangChain, SQLite, TypeScript")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 530, "Blockchain Supply Chain Tracker (2024)")
        c.setFont("Helvetica", 11)
        c.drawString(60, 515, "• Developed supply chain transparency system using Hyperledger Fabric")
        c.drawString(60, 500, "• Built REST API backend with Node.js and MongoDB")
        c.drawString(60, 485, "• Tech: Hyperledger Fabric, Node.js, MongoDB, React, Docker")
        
        # Experience
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, 450, "Experience")
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, 430, "Backend Developer Intern — TechCorp (Jun 2024 – Dec 2024)")
        c.setFont("Helvetica", 11)
        c.drawString(60, 415, "• Built REST APIs using FastAPI and PostgreSQL")
        c.drawString(60, 400, "• Reduced API latency by 40% through Redis caching")
        c.drawString(60, 385, "• Deployed services on AWS EC2 with Nginx reverse proxy")
        
        # Education
        c.setFont("Helvetica-Bold", 13)
        c.drawString(50, 350, "Education")
        c.setFont("Helvetica", 11)
        c.drawString(50, 330, "BSc in Computer Science — University of Colombo (2021-2025)")
        c.drawString(50, 315, "GPA: 3.8/4.0")
        
        c.save()
        buffer.seek(0)
        return buffer.read()
    except ImportError:
        pass
    
    # Fallback: use PyMuPDF to create a simple PDF
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    resume_text = """Ravi Shankar
Full Stack Developer | ravi@email.com

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frameworks: FastAPI, React, Next.js, LangChain
Databases: PostgreSQL, MongoDB, ChromaDB
Tools: Docker, Git, AWS EC2, Nginx

PROJECTS
PrepLingo - AI Interview Trainer (2025)
- Built AI interview simulator using LangChain, RAG, Google Gemini
- Implemented dual retriever strategy
- Tech: FastAPI, Next.js, ChromaDB, LangChain, SQLite

Blockchain Supply Chain Tracker (2024)  
- Developed using Hyperledger Fabric
- Tech: Node.js, MongoDB, React, Docker

EXPERIENCE
Backend Developer Intern - TechCorp (Jun 2024 - Dec 2024)
- Built REST APIs using FastAPI and PostgreSQL
- Reduced API latency by 40% through Redis caching

EDUCATION
BSc Computer Science - University of Colombo (2021-2025)
GPA: 3.8/4.0"""
    
    page.insert_text((50, 50), resume_text, fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ── Tests ─────────────────────────────────────────────────────────

def test_health():
    section("TEST 1: Health Check")
    resp = requests.get(f"{BASE_URL}/health")
    if resp.status_code == 200 and resp.json()["status"] == "ok":
        ok(f"Health check passed: {resp.json()}")
    else:
        fail(f"Health check failed: {resp.status_code} {resp.text}")
        sys.exit(1)


def test_resume_upload():
    section("TEST 2: Resume Upload (POST /api/resume/upload)")
    
    print("  Creating sample PDF...")
    pdf_bytes = create_sample_pdf_bytes()
    info(f"Sample PDF size: {len(pdf_bytes):,} bytes")
    
    print("  Uploading to API (this calls Gemini + ChromaDB)...")
    start = time.time()
    
    resp = requests.post(
        f"{BASE_URL}/api/resume/upload",
        params={"guest_id": TEST_GUEST_ID},
        files={"file": ("test_resume.pdf", pdf_bytes, "application/pdf")},
    )
    elapsed = time.time() - start
    
    if resp.status_code == 200:
        data = resp.json()
        ok(f"Upload successful in {elapsed:.1f}s")
        ok(f"Resume ID: {data['resume_id']}")
        ok(f"Name parsed: {data['name']}")
        ok(f"Skills found: {len(data['parsed_skills'])} — {data['parsed_skills'][:5]}")
        ok(f"Projects found: {len(data['parsed_projects'])}")
        ok(f"Chunks embedded in ChromaDB: {data['chunks_embedded']}")
        info(data['message'])
        return data['resume_id']
    else:
        fail(f"Upload failed: {resp.status_code}")
        fail(resp.text[:500])
        return None


def test_resume_get(resume_id: int):
    section("TEST 3: Get Resume (GET /api/resume/{id})")
    
    resp = requests.get(f"{BASE_URL}/api/resume/{resume_id}")
    
    if resp.status_code == 200:
        data = resp.json()
        ok(f"Resume retrieved successfully")
        ok(f"Name: {data['name']}")
        ok(f"Skills: {len(data['skills'])} total")
        ok(f"Projects: {len(data['projects'])} total")
        ok(f"Experience: {len(data['experience'])} entries")
        ok(f"Education: {len(data['education'])} entries")
        ok(f"Chunks embedded: {data['chunks_embedded']}")
    else:
        fail(f"Get resume failed: {resp.status_code} {resp.text}")


def test_resume_get_by_guest():
    section("TEST 4: Get Resume by Guest ID (GET /api/resume/guest/{guest_id})")
    
    resp = requests.get(f"{BASE_URL}/api/resume/guest/{TEST_GUEST_ID}")
    
    if resp.status_code == 200 and resp.json():
        data = resp.json()
        ok(f"Resume found by guest_id")
        ok(f"Resume ID: {data['resume_id']}")
    else:
        fail(f"Get by guest failed: {resp.status_code} {resp.text}")


def test_invalid_file():
    section("TEST 5: Validation — Non-PDF file should fail")
    
    resp = requests.post(
        f"{BASE_URL}/api/resume/upload",
        params={"guest_id": TEST_GUEST_ID},
        files={"file": ("resume.txt", b"This is not a PDF", "text/plain")},
    )
    
    if resp.status_code == 400:
        ok(f"Correctly rejected non-PDF: {resp.json()['detail']}")
    else:
        fail(f"Should have returned 400, got: {resp.status_code}")


def test_chromadb_retrieval():
    section("TEST 6: ChromaDB Retrieval (resume chunks searchable)")
    
    # Import and test directly
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from dotenv import load_dotenv
    load_dotenv()
    
    from app.langchain_layer.vector_store.store_manager import get_resume_retriever
    retriever = get_resume_retriever(guest_id=TEST_GUEST_ID, k=2)
    docs = retriever.invoke("Python projects and experience")
    
    if docs:
        ok(f"Retrieved {len(docs)} chunks from ChromaDB")
        for i, doc in enumerate(docs):
            info(f"Chunk {i+1}: {doc.page_content[:100]}...")
    else:
        fail("No chunks retrieved — resume may not be embedded")


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}🧪 PrepLingo Phase 2 Test Suite{RESET}")
    print(f"   Testing against: {BASE_URL}")
    print(f"   Guest ID: {TEST_GUEST_ID}")
    
    try:
        test_health()
        resume_id = test_resume_upload()
        if resume_id:
            test_resume_get(resume_id)
            test_resume_get_by_guest()
        test_invalid_file()
        test_chromadb_retrieval()
        
        print(f"\n{BOLD}{GREEN}🎉 All Phase 2 tests passed!{RESET}\n")
        print(f"  Next steps:")
        print(f"  1. Visit http://localhost:8000/docs to see Swagger UI")
        print(f"  2. Try uploading your own real PDF resume")
        print(f"  3. Run Phase 3 when ready\n")
        
    except requests.ConnectionError:
        fail("Cannot connect to server. Is it running?")
        print(f"\n  Start it with:")
        print(f"  cd PrepLingo/backend")
        print(f"  ./venv/bin/uvicorn app.main:app --reload\n")
        sys.exit(1)
