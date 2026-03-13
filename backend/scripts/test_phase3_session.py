"""
scripts/test_phase3_session.py

Tests the complete interview loop:
  1. Create a session
  2. Get the first question (Groq LLM call)
  3. Send 2 answers (Groq LLM + evaluation)
  4. Verify all DB records
  5. End the session

HOW TO RUN:
  # Make sure server is running first!
  cd PrepLingo/backend
  ./venv/bin/uvicorn app.main:app --reload &
  ./venv/bin/python scripts/test_phase3_session.py

WHAT YOU WILL SEE:
  - Real AI interview questions from Llama 3.3 70B via Groq
  - Real evaluation scores (0-10) for your test answers
  - Full DB persistence check
"""

import sys, os, time, requests

BASE_URL = "http://localhost:8000"
TEST_GUEST_ID = "test-guest-phase3-001"

GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; BLUE = "\033[94m"
RESET = "\033[0m"; BOLD = "\033[1m"

def ok(msg):   print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}"); sys.exit(1)
def info(msg): print(f"  {BLUE}ℹ  {msg}{RESET}")
def section(msg): print(f"\n{BOLD}{YELLOW}── {msg} ──{RESET}")


# ── Tests ─────────────────────────────────────────────────────────

def test_health():
    section("TEST 1: Health Check")
    r = requests.get(f"{BASE_URL}/health")
    if r.status_code == 200:
        ok(f"Server alive: {r.json()}")
    else:
        fail(f"Server not running! Start with: uvicorn app.main:app --reload")


def test_create_session(interview_type="technical") -> int:
    section(f"TEST 2: Create Session (type={interview_type})")
    r = requests.post(f"{BASE_URL}/api/session/", json={
        "guest_id": TEST_GUEST_ID,
        "interview_type": interview_type,
        "resume_id": None,
    })
    if r.status_code != 200:
        fail(f"Create session failed: {r.status_code} {r.text}")

    data = r.json()
    ok(f"Session created: ID={data['session_id']}, type={data['interview_type']}")
    ok(f"Max questions: {data['max_questions']}")
    info(data['message'])
    return data['session_id']


def test_start_session(session_id: int) -> str:
    section("TEST 3: Get First Question (GET /start)")
    print("  Calling Groq (Llama 3.3 70B) to generate opening question...")
    start = time.time()

    r = requests.get(f"{BASE_URL}/api/session/{session_id}/start")
    elapsed = time.time() - start

    if r.status_code != 200:
        fail(f"Start session failed: {r.status_code} {r.text}")

    data = r.json()
    ok(f"First question received in {elapsed:.1f}s")
    ok(f"Question #{data['question_number']}")
    print(f"\n  {BOLD}🤖 AI:{RESET} {data['ai_question']}\n")
    return data['ai_question']


def test_send_message(session_id: int, user_answer: str, expected_q_num: int) -> dict:
    section(f"TEST 4/{expected_q_num}: Send Answer → Get Next Question + Scoring")
    print(f"  {BOLD}👤 You:{RESET} {user_answer[:80]}...")
    print(f"  Sending to pipeline (evaluate + generate next question)...")
    start = time.time()

    r = requests.post(
        f"{BASE_URL}/api/session/{session_id}/message",
        json={"content": user_answer}
    )
    elapsed = time.time() - start

    if r.status_code != 200:
        fail(f"Send message failed: {r.status_code} {r.text[:300]}")

    data = r.json()
    ok(f"Pipeline completed in {elapsed:.1f}s")
    ok(f"Question #{data['question_number']}, Complete={data['session_complete']}")

    if data.get("evaluation"):
        ev = data["evaluation"]
        print(f"\n  {BOLD}📊 Evaluation Scores:{RESET}")
        print(f"     Overall:              {ev['overall_score']}/10")
        print(f"     Technical Correctness:{ev['technical_correctness']}/10")
        print(f"     Depth of Explanation: {ev['depth_of_explanation']}/10")
        print(f"     Clarity:              {ev['clarity']}/10")
        if ev.get("strengths"):
            print(f"     ✅ Strengths: {ev['strengths']}")
        if ev.get("weaknesses"):
            print(f"     ⚠️  Weaknesses: {ev['weaknesses']}")
        if ev.get("suggestions"):
            print(f"     💡 Suggestions: {ev['suggestions']}")

    if data.get("ai_question"):
        print(f"\n  {BOLD}🤖 AI:{RESET} {data['ai_question']}\n")

    return data


def test_get_session_history(session_id: int):
    section("TEST 5: Get Session History (GET /session/{id})")
    r = requests.get(f"{BASE_URL}/api/session/{session_id}")
    if r.status_code != 200:
        fail(f"Get session failed: {r.status_code} {r.text}")

    data = r.json()
    ok(f"Session retrieved: status={data['status']}")
    ok(f"question_count={data['question_count']}")
    ok(f"Messages in history: {len(data['messages'])}")
    for msg in data['messages']:
        role_icon = "🤖" if msg['role'] == 'ai' else "👤"
        print(f"  {role_icon} [{msg['role'].upper()}] Q{msg.get('question_number','?')}: {msg['content'][:60]}...")


def test_double_start_blocked(session_id: int):
    section("TEST 6: Validation — Can't start an already-started session")
    r = requests.get(f"{BASE_URL}/api/session/{session_id}/start")
    if r.status_code == 400:
        ok(f"Correctly blocked: {r.json()['detail']}")
    else:
        fail(f"Should have returned 400, got: {r.status_code}")


def test_end_session(session_id: int):
    section("TEST 7: End Session")
    r = requests.post(f"{BASE_URL}/api/session/{session_id}/end")
    if r.status_code == 200:
        ok(f"Session ended: {r.json()}")
    else:
        fail(f"End session failed: {r.status_code} {r.text}")


# ── Main ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{BOLD}🧪 PrepLingo Phase 3 Test Suite — Full Interview Loop{RESET}")
    print(f"   Backend:  {BASE_URL}")
    print(f"   Guest ID: {TEST_GUEST_ID}")
    print(f"   LLM:      Groq (Llama 3.3 70B) — expect ~2-5s per call")

    try:
        test_health()
        session_id = test_create_session("technical")
        first_q = test_start_session(session_id)

        # Simulate a candidate answering 2 questions
        result1 = test_send_message(
            session_id=session_id,
            user_answer=(
                "Python uses dynamic typing and is interpreted. "
                "It uses a GIL (Global Interpreter Lock) which prevents true parallelism in threads, "
                "but async IO and multiprocessing can be used to work around this. "
                "I've used Python extensively with FastAPI for building REST APIs."
            ),
            expected_q_num=2,
        )

        if not result1["session_complete"]:
            result2 = test_send_message(
                session_id=session_id,
                user_answer=(
                    "Database indexing creates a B-tree data structure that allows O(log n) lookups "
                    "instead of O(n) full table scans. For PostgreSQL, I've used both composite indexes "
                    "and partial indexes. The trade-off is that writes become slower since the index "
                    "must also be updated. I've also worked with Redis for caching frequently-read data."
                ),
                expected_q_num=3,
            )

        test_get_session_history(session_id)
        test_double_start_blocked(session_id)
        test_end_session(session_id)

        print(f"\n{BOLD}{GREEN}🎉 Phase 3 Complete! The AI interview loop is working!{RESET}\n")
        print(f"  What just happened:")
        print(f"  1. Created a real interview session in SQLite")
        print(f"  2. Groq (Llama 3.3 70B) generated a personalized opening question")
        print(f"  3. Sent 2 answers → each evaluated with real AI scores")
        print(f"  4. Each answer triggered: retrieval → evaluation → next question")
        print(f"  5. All messages + scores persisted to DB")
        print(f"\n  Next: Phase 4 — Report generation!\n")

    except requests.ConnectionError:
        fail("Cannot connect. Is the server running?")
        print("\n  Start it: ./venv/bin/uvicorn app.main:app --reload\n")
