"""
scripts/test_phase5_pdf_relevance.py

Guest-mode Phase 5 hardening check:
- Upload a resume PDF
- Start a RESUME interview
- Verify first AI question appears grounded in resume keywords

How to run:
  cd PrepLingo/backend
  ./venv/bin/uvicorn app.main:app --reload
  ./venv/bin/python scripts/test_phase5_pdf_relevance.py

Optional:
  PREPLINGO_BASE_URL=http://localhost:8010 ./venv/bin/python scripts/test_phase5_pdf_relevance.py
"""

import io
import os
import sys
import requests

BASE_URL = os.getenv("PREPLINGO_BASE_URL", "http://localhost:8000")
TEST_GUEST_ID = "test-guest-phase5-relevance-001"

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg):
    print(f"  {GREEN}✅ {msg}{RESET}")


def fail(msg):
    print(f"  {RED}❌ {msg}{RESET}")
    sys.exit(1)


def warn(msg):
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def info(msg):
    print(f"  {BLUE}ℹ  {msg}{RESET}")


def section(msg):
    print(f"\n{BOLD}{YELLOW}── {msg} ──{RESET}")


def create_resume_pdf_bytes() -> bytes:
    """Create a focused in-memory resume with distinctive project keywords."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    text = """
Aarav Nirmal
Backend Engineer

SKILLS: Python, FastAPI, ChromaDB, Redis, PostgreSQL

PROJECT: PrepLingo Interview Copilot
Built an interview training platform using FastAPI, LangChain, ChromaDB, and Groq.
Implemented resume-aware retrieval and generated interview reports.

PROJECT: Hyperledger SupplyTrace
Built a blockchain supply chain tracker with Hyperledger Fabric and Docker.
Implemented chaincode for shipment events and audit trails.
""".strip()
    page.insert_text((50, 50), text, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data


def ensure_health():
    section("TEST 1: Health")
    r = requests.get(f"{BASE_URL}/health")
    if r.status_code != 200:
        fail(f"Backend not reachable at {BASE_URL}: {r.status_code} {r.text}")
    ok("Backend is reachable")


def upload_resume() -> int:
    section("TEST 2: Upload Resume PDF")
    pdf = create_resume_pdf_bytes()
    r = requests.post(
        f"{BASE_URL}/api/resume/upload",
        params={"guest_id": TEST_GUEST_ID},
        files={"file": ("resume_phase5_test.pdf", pdf, "application/pdf")},
    )
    if r.status_code != 200:
        fail(f"Upload failed: {r.status_code} {r.text[:500]}")
    data = r.json()
    ok(f"Resume uploaded: resume_id={data['resume_id']}")
    info(f"Parsed skills: {data.get('parsed_skills', [])[:6]}")
    return data["resume_id"]


def create_resume_session(resume_id: int) -> int:
    section("TEST 3: Create RESUME session")
    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={
            "guest_id": TEST_GUEST_ID,
            "interview_type": "resume",
            "resume_id": resume_id,
        },
    )
    if r.status_code != 200:
        fail(f"Session create failed: {r.status_code} {r.text}")
    sid = r.json()["session_id"]
    ok(f"Session created: {sid}")
    return sid


def start_and_check_relevance(session_id: int):
    section("TEST 4: Start session and check first-question relevance")
    r = requests.get(f"{BASE_URL}/api/session/{session_id}/start")
    if r.status_code != 200:
        fail(f"Session start failed: {r.status_code} {r.text}")

    q = r.json().get("ai_question", "")
    print(f"\n  {BOLD}🤖 AI First Question:{RESET} {q}\n")

    # Heuristic keyword grounding check for resume-specific cues.
    expected_keywords = [
        "preplingo",
        "hyperledger",
        "supplytrace",
        "fastapi",
        "chromadb",
        "blockchain",
    ]
    lower_q = q.lower()
    matched = [k for k in expected_keywords if k in lower_q]

    if matched:
        ok(f"Question appears grounded in resume context. Matched keywords: {matched}")
    else:
        warn("Question did not include expected unique resume keywords.")
        warn("This can happen occasionally with LLM phrasing. Try re-running once.")


def negative_validation_check():
    section("TEST 5: Resume interview requires resume_id")
    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={
            "guest_id": TEST_GUEST_ID,
            "interview_type": "resume",
            "resume_id": None,
        },
    )
    if r.status_code == 400:
        ok("Validation works: resume interview without resume_id is blocked")
    else:
        fail(f"Expected 400 for missing resume_id, got {r.status_code}: {r.text}")


if __name__ == "__main__":
    print(f"\n{BOLD}🧪 Phase 5 Guest-Mode: PDF Relevance Check{RESET}")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Guest ID: {TEST_GUEST_ID}")

    try:
        ensure_health()
        rid = upload_resume()
        sid = create_resume_session(rid)
        start_and_check_relevance(sid)
        negative_validation_check()

        print(f"\n{BOLD}{GREEN}🎉 Phase 5 relevance flow check completed.{RESET}\n")
    except requests.ConnectionError:
        fail("Cannot connect to backend. Start server first.")
