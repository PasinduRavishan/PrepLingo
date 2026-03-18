"""
scripts/test_phase5_edge_cases.py

Phase 5 guest-mode hardening edge-case checks.

Covers:
1) resume interview without resume_id -> 400
2) resume_id ownership mismatch -> 403
3) message before session start -> 400
4) report requested before completion -> 400
5) get latest resume by guest returns newest record

How to run:
  cd PrepLingo/backend
  ./venv/bin/uvicorn app.main:app --reload
  ./venv/bin/python scripts/test_phase5_edge_cases.py

Optional:
  PREPLINGO_BASE_URL=http://localhost:8010 ./venv/bin/python scripts/test_phase5_edge_cases.py
"""

import json
import os
import sys
from datetime import datetime

import requests
from sqlmodel import Session, select

# Add backend root to imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.models.resume import Resume
from app.models.session import InterviewSession

BASE_URL = os.getenv("PREPLINGO_BASE_URL", "http://localhost:8000")

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


def info(msg):
    print(f"  {BLUE}ℹ  {msg}{RESET}")


def section(msg):
    print(f"\n{BOLD}{YELLOW}── {msg} ──{RESET}")


def ensure_health():
    section("TEST 1: Health")
    r = requests.get(f"{BASE_URL}/health")
    if r.status_code != 200:
        fail(f"Backend not reachable at {BASE_URL}: {r.status_code} {r.text}")
    ok("Backend reachable")


def seed_resume(guest_id: str, name: str) -> int:
    with Session(engine) as db:
        resume = Resume(
            guest_id=guest_id,
            raw_text=f"Resume for {name}",
            parsed_data=json.dumps({"name": name, "skills": ["Python"]}),
            chunks_embedded=False,
            created_at=datetime.utcnow(),
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume.id


def create_technical_session(guest_id: str) -> int:
    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={"guest_id": guest_id, "interview_type": "technical", "resume_id": None},
    )
    if r.status_code != 200:
        fail(f"Failed to create technical session: {r.status_code} {r.text}")
    sid = r.json()["session_id"]
    info(f"Technical session created: {sid}")
    return sid


def test_resume_session_requires_resume_id():
    section("TEST 2: resume interview requires resume_id")
    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={"guest_id": "phase5-guest-a", "interview_type": "resume", "resume_id": None},
    )
    if r.status_code != 400:
        fail(f"Expected 400, got {r.status_code}: {r.text}")
    ok("Blocked missing resume_id for resume interview")


def test_resume_ownership_guard():
    section("TEST 3: resume ownership mismatch blocked")
    owner_guest = "phase5-owner-guest"
    other_guest = "phase5-other-guest"
    resume_id = seed_resume(owner_guest, "Owner Candidate")

    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={"guest_id": other_guest, "interview_type": "resume", "resume_id": resume_id},
    )
    if r.status_code != 403:
        fail(f"Expected 403 ownership block, got {r.status_code}: {r.text}")
    ok("Ownership mismatch correctly blocked")


def test_message_before_start_blocked():
    section("TEST 4: sending message before /start blocked")
    sid = create_technical_session("phase5-message-before-start")
    r = requests.post(
        f"{BASE_URL}/api/session/{sid}/message",
        json={"content": "This should be blocked before start"},
    )
    if r.status_code != 400:
        fail(f"Expected 400 before-start block, got {r.status_code}: {r.text}")
    ok("Message before start is blocked")


def test_report_before_completion_blocked():
    section("TEST 5: report before completion blocked")
    sid = create_technical_session("phase5-report-before-complete")
    r = requests.get(f"{BASE_URL}/api/report/{sid}")
    if r.status_code != 400:
        fail(f"Expected 400 report-before-complete, got {r.status_code}: {r.text}")
    ok("Report request blocked for incomplete session")


def test_latest_resume_by_guest():
    section("TEST 6: guest resume endpoint returns latest")
    guest = "phase5-latest-resume-guest"
    first_id = seed_resume(guest, "First Candidate")
    second_id = seed_resume(guest, "Second Candidate")

    r = requests.get(f"{BASE_URL}/api/resume/guest/{guest}")
    if r.status_code != 200:
        fail(f"Failed to fetch guest resume: {r.status_code} {r.text}")
    data = r.json()
    if not data:
        fail("Expected resume payload, got null")
    if data["resume_id"] != second_id:
        fail(f"Expected latest resume_id {second_id}, got {data['resume_id']} (first was {first_id})")
    ok("Latest resume is returned deterministically")


if __name__ == "__main__":
    print(f"\n{BOLD}🧪 Phase 5 Edge Case Regression Suite{RESET}")
    print(f"   Base URL: {BASE_URL}")

    try:
        ensure_health()
        test_resume_session_requires_resume_id()
        test_resume_ownership_guard()
        test_message_before_start_blocked()
        test_report_before_completion_blocked()
        test_latest_resume_by_guest()

        print(f"\n{BOLD}{GREEN}🎉 Phase 5 edge-case checks passed.{RESET}\n")
    except requests.ConnectionError:
        fail("Cannot connect to backend. Start server first.")
