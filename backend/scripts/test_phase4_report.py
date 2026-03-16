"""
scripts/test_phase4_report.py

Phase 4 integration test for report generation.

What this validates:
1. Create session via API
2. Seed deterministic evaluations in DB
3. Mark session as completed
4. GET /api/report/{session_id} generates report
5. GET again returns same report (idempotent)
6. GET with regenerate=true recalculates after new evaluation

How to run:
  cd PrepLingo/backend
  ./venv/bin/uvicorn app.main:app --reload
  ./venv/bin/python scripts/test_phase4_report.py
"""

import os
import sys
from datetime import datetime

import requests

# Add project root for `from app...` imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select

from app.db.database import engine
from app.models.evaluation import Evaluation
from app.models.message import Message, MessageRole
from app.models.report import Report
from app.models.session import InterviewSession, SessionStatus


BASE_URL = os.getenv("PREPLINGO_BASE_URL", "http://localhost:8000")
TEST_GUEST_ID = "test-guest-phase4-001"

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


def test_health():
    section("TEST 1: Health Check")
    r = requests.get(f"{BASE_URL}/health")
    if r.status_code == 200:
        ok(f"Server alive: {r.json()}")
    else:
        fail(f"Server not running. Start with: uvicorn app.main:app --reload")


def create_session() -> int:
    section("TEST 2: Create Session")
    r = requests.post(
        f"{BASE_URL}/api/session/",
        json={
            "guest_id": TEST_GUEST_ID,
            "interview_type": "technical",
            "resume_id": None,
        },
    )
    if r.status_code != 200:
        fail(f"Create session failed: {r.status_code} {r.text}")
    session_id = r.json()["session_id"]
    ok(f"Session created: {session_id}")
    return session_id


def seed_completed_session_with_evaluations(session_id: int):
    section("TEST 3: Seed Evaluations + Complete Session")
    with Session(engine) as db:
        session = db.get(InterviewSession, session_id)
        if not session:
            fail(f"Session {session_id} not found in DB")

        # Clean old rows for deterministic re-run behavior.
        existing_reports = db.exec(select(Report).where(Report.session_id == session_id)).all()
        for row in existing_reports:
            db.delete(row)

        existing_evals = db.exec(select(Evaluation).where(Evaluation.session_id == session_id)).all()
        for row in existing_evals:
            db.delete(row)

        existing_msgs = db.exec(select(Message).where(Message.session_id == session_id)).all()
        for row in existing_msgs:
            db.delete(row)

        db.flush()

        seeded_scores = [7, 8, 6]
        seeded_dims = [
            {"tc": 7, "depth": 7, "clarity": 8},
            {"tc": 8, "depth": 8, "clarity": 7},
            {"tc": 6, "depth": 6, "clarity": 7},
        ]

        for idx, score in enumerate(seeded_scores, start=1):
            msg = Message(
                session_id=session_id,
                role=MessageRole.USER,
                content=f"Seeded answer {idx}",
                question_number=idx,
                ai_question_asked=f"Seeded question {idx}",
            )
            db.add(msg)
            db.flush()

            evaluation = Evaluation(
                session_id=session_id,
                message_id=msg.id,
                question_number=idx,
                technical_correctness=seeded_dims[idx - 1]["tc"],
                depth_of_explanation=seeded_dims[idx - 1]["depth"],
                clarity=seeded_dims[idx - 1]["clarity"],
                overall_score=score,
                strengths='["Clear explanation", "Good structure"]',
                weaknesses='["Could add more detail"]',
                suggestions='["Practice deeper trade-off analysis"]',
            )
            db.add(evaluation)

        session.status = SessionStatus.COMPLETED
        session.question_count = 3
        session.ended_at = datetime.utcnow()
        db.add(session)
        db.commit()

    ok("Seed data inserted and session marked completed")


def fetch_report(session_id: int, regenerate: bool = False) -> dict:
    url = f"{BASE_URL}/api/report/{session_id}"
    if regenerate:
        url += "?regenerate=true"
    r = requests.get(url)
    if r.status_code != 200:
        fail(f"Report request failed: {r.status_code} {r.text}")
    return r.json()


def test_generate_report(session_id: int) -> dict:
    section("TEST 4: Generate Report (GET /api/report/{id})")
    data = fetch_report(session_id)
    ok(f"Report generated with report_id={data['report_id']}")
    ok(f"Overall score: {data['overall_score']}")
    ok(f"Per-question scores: {data['per_question_scores']}")
    ok(f"Per-dimension scores: {data['per_dimension_scores']}")

    # Basic semantic checks
    if data["session_id"] != session_id:
        fail("session_id mismatch in report response")
    if not data["per_question_scores"] or len(data["per_question_scores"]) != 3:
        fail("Expected 3 per-question scores")
    if "technical_correctness" not in data["per_dimension_scores"]:
        fail("Missing technical_correctness in per_dimension_scores")

    return data


def test_idempotent_fetch(session_id: int, first_report_id: int):
    section("TEST 5: Idempotent Fetch")
    second = fetch_report(session_id)
    if second["report_id"] != first_report_id:
        fail("Expected same report_id on second fetch")
    ok("Second fetch returned existing persisted report")


def add_one_more_evaluation(session_id: int):
    section("TEST 6: Add New Evaluation Then Regenerate")
    with Session(engine) as db:
        msg = Message(
            session_id=session_id,
            role=MessageRole.USER,
            content="Seeded answer 4",
            question_number=4,
            ai_question_asked="Seeded question 4",
        )
        db.add(msg)
        db.flush()

        evaluation = Evaluation(
            session_id=session_id,
            message_id=msg.id,
            question_number=4,
            technical_correctness=9,
            depth_of_explanation=9,
            clarity=9,
            overall_score=9,
            strengths='["Excellent depth"]',
            weaknesses='[]',
            suggestions='["Keep practicing at this level"]',
        )
        db.add(evaluation)
        db.commit()
    ok("Added a fourth evaluation")


def test_regenerate(session_id: int, old_overall: float):
    regenerated = fetch_report(session_id, regenerate=True)
    ok(f"Regenerated report overall score: {regenerated['overall_score']}")
    if len(regenerated["per_question_scores"]) != 4:
        fail("Expected 4 per-question scores after regeneration")
    if regenerated["overall_score"] <= old_overall:
        fail("Expected overall score to increase after adding stronger evaluation")
    ok("Regeneration recalculated metrics correctly")


if __name__ == "__main__":
    print(f"\n{BOLD}🧪 PrepLingo Phase 4 Test Suite — Report Service{RESET}")
    print(f"   Backend: {BASE_URL}")
    print(f"   Guest ID: {TEST_GUEST_ID}")

    try:
        test_health()
        sid = create_session()
        seed_completed_session_with_evaluations(sid)
        initial = test_generate_report(sid)
        test_idempotent_fetch(sid, initial["report_id"])
        add_one_more_evaluation(sid)
        test_regenerate(sid, initial["overall_score"])

        print(f"\n{BOLD}{GREEN}🎉 Phase 4 report tests passed!{RESET}\n")
        info("Report generation, persistence, idempotency, and regeneration are working.")
    except requests.ConnectionError:
        fail("Cannot connect to server. Start with: ./venv/bin/uvicorn app.main:app --reload")
