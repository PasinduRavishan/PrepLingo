"""
services/session_service.py — The Interview Orchestrator

THIS IS THE MOST IMPORTANT FILE IN THE BACKEND.

It ties together EVERY LangChain component we built:
  - DualRetriever   → fetches resume + knowledge context
  - QuestionChain   → generates the next interview question
  - EvaluationChain → scores the user's answer (0-10 per dimension)
  - SessionMemory   → manages conversation history per session

THE INTERVIEW FLOW (what happens when user clicks "Send"):

  User types answer → POST /api/session/{id}/message
         │
         ▼
  session_service.process_message()
         │
         ├── 1. Load session from DB (validate it's still active)
         │
         ├── 2. Validate: did user already finish? (question_count >= max)
         │
         ├── 3. Load conversation history from SessionMemory
         │
         ├── 4. Build DualRetriever (resume chunks + domain knowledge)
         │
         ├── 5A. If NOT first message → Run EvaluationChain
         │        ┌─ Gets the question that was just answered from DB
         │        └─ Scores answer: technical, depth, clarity (0-10 each)
         │
         ├── 5B. Save user's answer to DB (with the AI question it answered)
         │
         ├── 6. Run QuestionChain → generates NEXT question
         │        ┌─ retriever |> format → context string
         │        ├─ history from SessionMemory
         │        └─ Groq LLM (Llama 3.3 70B) → next question
         │
         ├── 7. Save AI question + evaluation to DB
         │
         ├── 8. Update SessionMemory with this exchange
         │
         ├── 9. Increment question_count. If >= max → mark COMPLETED
         │
         └── 10. Return {ai_question, evaluation, question_number, is_complete}


WHY SPLIT create_session AND first_question?
  create_session → just makes the DB row (fast, synchronous)
  get_first_question → calls Groq (slow, async, could fail)
  
  This separation means the session exists in the DB even if the 
  first Groq call fails. User can retry without recreating the session.

WHY IS EVALUATION RUN ASYNC BEFORE QUESTION GENERATION?
  Sequential (not parallel) because:
  1. We want evaluation scores BEFORE generating the next question
     (future: question difficulty could adapt based on score)
  2. Avoids parallel Groq calls (rate limits)
  3. Both still complete fast because Groq is ~10x faster than GPT-4
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Optional, Any

from sqlmodel import Session, select
from langchain_core.runnables import RunnableLambda

from app.models.session import InterviewSession, SessionStatus
from app.models.message import Message, MessageRole
from app.models.evaluation import Evaluation
from app.models.resume import Resume
from app.langchain_layer.retrievers.dual_retriever import build_dual_retriever, format_retrieved_docs
from app.langchain_layer.chains.question_chain import build_question_chain
from app.langchain_layer.chains.evaluation_chain import evaluate_answer
from app.langchain_layer.memory.session_memory import get_or_create_memory, save_exchange, get_history
from app.langchain_layer.prompts import get_prompt_for_type
from app.services.report_service import generate_or_get_report
from app.config import get_settings

settings = get_settings()


# Cache question chains per session so we don't rebuild retriever/prompt graph every turn.
_session_question_chains: dict[int, Any] = {}
_light_question_chains: dict[str, Any] = {}


def _fallback_question(interview_type: str, question_number: int) -> str:
    """Fast fallback question if LLM call exceeds timeout or fails."""
    technical_bank = [
        "Describe a recent bug you fixed, how you diagnosed it, and what trade-off you accepted.",
        "Explain a performance issue you investigated and the measurements that guided your fix.",
        "Walk through a feature you built end-to-end and justify one major design decision.",
        "Tell me about a difficult API integration and how you handled failures and retries.",
        "Describe a time you refactored risky code and how you verified correctness.",
    ]
    system_design_bank = [
        "Design a high-level architecture for a URL shortener and explain your scaling strategy.",
        "How would you design a notification service with reliable delivery and retry handling?",
        "Design a read-heavy dashboard backend and explain caching plus data freshness trade-offs.",
        "Design a file upload pipeline for large files, including validation and storage.",
        "Design a rate-limiting system for public APIs and explain key trade-offs.",
    ]
    behavioral_bank = [
        "Tell me about a time you had to influence stakeholders without direct authority.",
        "Describe a conflict on your team and how you resolved it constructively.",
        "Share an example of a failed approach and what you changed afterward.",
        "Tell me about a tight deadline and how you prioritized scope and quality.",
        "Describe a time you gave or received tough feedback and what happened next.",
    ]
    resume_bank = [
        "Choose one project from your resume and explain the architecture and your contribution.",
        "From your resume experience, describe a technical decision you would make differently now.",
        "Pick a resume project and explain how you measured success and outcomes.",
        "From your resume work, describe one major challenge and the mitigation you used.",
        "Walk through one resume project and explain a key scalability or reliability trade-off.",
    ]

    banks = {
        "technical": technical_bank,
        "system_design": system_design_bank,
        "behavioral": behavioral_bank,
        "resume": resume_bank,
    }
    bank = banks.get(interview_type, technical_bank)
    idx = max(question_number - 1, 0) % len(bank)
    return bank[idx]


def _normalize_question(text: str) -> str:
    lowered = (text or "").strip().lower()
    lowered = re.sub(r"^question\s*\d+\s*:\s*", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered


def _is_duplicate_question(candidate: str, previous_questions: list[str]) -> bool:
    cand = _normalize_question(candidate)
    if not cand:
        return True

    for prev in previous_questions:
        norm_prev = _normalize_question(prev)
        if not norm_prev:
            continue
        if cand == norm_prev:
            return True
        if cand in norm_prev or norm_prev in cand:
            return True

    return False


def _build_resume_profile_context(session: InterviewSession, db: Session) -> str:
    """Build a short resume profile string to ground questions when retrieval is sparse."""
    resume: Optional[Resume] = None

    if session.resume_id:
        resume = db.get(Resume, session.resume_id)

    if not resume:
        resume = db.exec(
            select(Resume)
            .where(Resume.guest_id == session.guest_id)
            .order_by(Resume.id.desc())
        ).first()

    if not resume or not resume.parsed_data:
        return ""

    try:
        parsed = json.loads(resume.parsed_data)
    except Exception:
        return ""

    skills = parsed.get("skills", [])[:8]
    projects = parsed.get("projects", [])[:2]

    project_lines = []
    for project in projects:
        if isinstance(project, dict):
            name = project.get("name", "")
            tech = project.get("tech_stack", [])
            tech_text = ", ".join(str(t) for t in tech[:4]) if isinstance(tech, list) else ""
            summary = f"{name}".strip()
            if tech_text:
                summary += f" [{tech_text}]"
            if summary:
                project_lines.append(summary)

    parts = []
    if skills:
        parts.append("skills=" + ", ".join(str(s) for s in skills))
    if project_lines:
        parts.append("projects=" + " | ".join(project_lines))

    if not parts:
        return ""

    return "Candidate resume profile: " + " ; ".join(parts)


def _load_resume_parsed(session: InterviewSession, db: Session) -> dict:
    resume: Optional[Resume] = None

    if session.resume_id:
        resume = db.get(Resume, session.resume_id)

    if not resume:
        resume = db.exec(
            select(Resume)
            .where(Resume.guest_id == session.guest_id)
            .order_by(Resume.id.desc())
        ).first()

    if not resume or not resume.parsed_data:
        return {}

    try:
        return json.loads(resume.parsed_data)
    except Exception:
        return {}


def _pick_topic_from_text(text: str, skill_candidates: list[str]) -> str:
    haystack = (text or "").lower()
    if not haystack:
        return ""

    builtins = [
        "next.js", "nextjs", "ssr", "ssg", "react", "python", "fastapi", "redis",
        "sql", "postgres", "docker", "kubernetes", "api", "cache", "caching",
    ]
    for topic in builtins:
        if topic in haystack:
            return topic

    for skill in skill_candidates:
        token = str(skill).strip().lower()
        if token and token in haystack:
            return token

    return ""


def _contextual_fallback_question(
    session: InterviewSession,
    db: Session,
    question_number: int,
    last_ai_question: str,
    user_answer: str,
) -> str:
    parsed = _load_resume_parsed(session, db)
    skills = parsed.get("skills", []) if isinstance(parsed, dict) else []
    projects = parsed.get("projects", []) if isinstance(parsed, dict) else []
    project_name = ""
    if projects and isinstance(projects[0], dict):
        project_name = str(projects[0].get("name", "")).strip()

    topic = _pick_topic_from_text(
        f"{last_ai_question}\n{user_answer}",
        [str(s) for s in skills[:12]],
    )

    if session.interview_type == "technical":
        if "ssr" in topic or "ssg" in topic or "next" in topic:
            where = f"in {project_name}" if project_name else "in one of your projects"
            return (
                f"{where.capitalize()}, when would you choose SSR over SSG, and how would you manage "
                "data freshness, cache invalidation, and deployment cost trade-offs?"
            )
        if topic:
            proj = f" from {project_name}" if project_name else ""
            return (
                f"You mentioned {topic}{proj}. Describe a production issue you faced with it, "
                "the metrics/logs you used to diagnose it, and the fix you shipped."
            )
        if project_name:
            return (
                f"In your {project_name} project, what was one key backend design decision, "
                "what alternatives did you reject, and why?"
            )

    return _fallback_question(session.interview_type, question_number)


async def _safe_generate_question(chain, payload: dict, interview_type: str, question_number: int) -> str:
    timeout = getattr(settings, "llm_timeout_seconds", 25)
    for attempt in range(2):
        try:
            return await asyncio.wait_for(chain.ainvoke(payload), timeout=timeout)
        except Exception as exc:
            print(f"   ⚠️ Question generation timeout/failure (attempt {attempt + 1}/2): {type(exc).__name__}: {exc!r}")
    return ""


async def _safe_evaluate_answer(question: str, user_answer: str, interview_type: str) -> dict:
    timeout = getattr(settings, "llm_timeout_seconds", 25)
    try:
        return await asyncio.wait_for(
            evaluate_answer(
                question=question,
                user_answer=user_answer,
                context=question,
                interview_type=interview_type,
            ),
            timeout=timeout,
        )
    except Exception as exc:
        print(f"   ⚠️ Evaluation timeout/failure: {exc}")
        return {
            "technical_correctness": 5,
            "depth_of_explanation": 5,
            "clarity": 5,
            "overall_score": 5,
            "strengths": ["Answer submitted"],
            "weaknesses": ["Evaluation timed out"],
            "suggestions": ["Keep answers concise and structured"],
        }


def _get_or_create_session_chain(session: InterviewSession):
    chain = _session_question_chains.get(session.id)
    if chain is not None:
        return chain

    retriever = build_dual_retriever(
        guest_id=session.guest_id,
        interview_type=session.interview_type,
    )
    prompt = get_prompt_for_type(session.interview_type)
    chain = build_question_chain(retriever, prompt)
    _session_question_chains[session.id] = chain
    return chain


def _get_or_create_light_chain(interview_type: str):
    chain = _light_question_chains.get(interview_type)
    if chain is not None:
        return chain

    prompt = get_prompt_for_type(interview_type)
    retriever = RunnableLambda(lambda _query: [])
    chain = build_question_chain(retriever, prompt)
    _light_question_chains[interview_type] = chain
    return chain


# ── Step 1: Create Session ─────────────────────────────────────────

def create_session(
    guest_id: str,
    interview_type: str,
    db: Session,
    resume_id: Optional[int] = None,
) -> InterviewSession:
    """
    Create a new InterviewSession row in the database.

    WHY NOT async?
      We're only writing to SQLite — no network calls needed.
      db.add() + db.commit() are synchronous SQLAlchemy operations.
      Only LLM calls need to be async.

    Returns the created session so the caller can use session.id
    to build the /message URL.
    """
    session = InterviewSession(
        guest_id=guest_id,
        interview_type=interview_type,
        resume_id=resume_id,
        status=SessionStatus.IN_PROGRESS,
        question_count=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)  # refresh loads the auto-generated id
    print(f"✅ Created session {session.id} | type={interview_type} | guest={guest_id[:8]}...")
    return session


# ── Step 2: Generate First Question ───────────────────────────────

async def get_first_question(
    session: InterviewSession,
    db: Session,
) -> dict:
    """
    Generate the opening question for a session.

    WHY A SEPARATE FUNCTION?
      The very first turn has no user answer to evaluate.
      We just want: "Hello! Let's start. Tell me about your experience with X."
      
      We use "start" as a seed input — the retriever uses it to find
      relevant context from the resume. The prompt instructs the LLM
      to introduce itself and ask the first question.

    Returns:
        {"ai_question": str, "question_number": 1, "session_id": int}
    """
    profile_context = _build_resume_profile_context(session, db)
    seed_input = "start introduction background experience"
    if profile_context:
        seed_input = f"{seed_input}\n\n{profile_context}"

    # Keep first-question latency low: skip vector retrieval on the opening turn.
    # We switch to full dual-retriever chain from question 2 onward.
    retriever = RunnableLambda(lambda _query: [])

    # Get the prompt template for this interview type
    prompt = get_prompt_for_type(session.interview_type)

    # Build the LCEL question chain
    chain = build_question_chain(retriever, prompt)

    print(f"🤖 Generating opening question for session {session.id}...")
    first_question = await _safe_generate_question(
        chain=chain,
        payload={
        "user_answer": seed_input,
        "question_number": 1,
        "history": [],  # Empty at start
        },
        interview_type=session.interview_type,
        question_number=1,
    )
    if not first_question or not first_question.strip():
        first_question = _contextual_fallback_question(
            session=session,
            db=db,
            question_number=1,
            last_ai_question="",
            user_answer=seed_input,
        )

    # Save as AI message in DB (question_number=1)
    ai_msg = Message(
        session_id=session.id,
        role=MessageRole.AI,
        content=first_question,
        question_number=1,
    )
    db.add(ai_msg)

    # Update session: question 1 is now active
    session.question_count = 1
    db.add(session)
    db.commit()

    print(f"   ✅ First question generated for session {session.id}")
    return {
        "ai_question": first_question,
        "question_number": 1,
        "session_id": session.id,
        "session_complete": False,
        "evaluation": None,
    }


# ── Step 3: Process Each Message (The Main Loop) ──────────────────

async def process_message(
    session_id: int,
    user_answer: str,
    db: Session,
) -> dict:
    """
    THE CORE OF THE INTERVIEW — called every time the user sends an answer.

    Full pipeline:
    1. Load + validate session
    2. Find the question that was just answered
    3. Evaluate the answer (async Groq call)
    4. Save user's answer to DB
    5. Save evaluation to DB
    6. Generate the NEXT question (async Groq call)
    7. Save AI question to DB
    8. Update conversation memory
    9. Increment question count
    10. Return everything the frontend needs

    Args:
        session_id: int — the active session
        user_answer: str — what the candidate typed
        db: SQLModel Session — database connection

    Returns:
        {
          "ai_question": "What happens when you have cache miss in Redis?",
          "question_number": 4,
          "evaluation": {
            "overall_score": 7,
            "technical_correctness": 8,
            ...
            "strengths": ["Good explanation of..."],
            "weaknesses": ["Missed mention of..."],
            "suggestions": ["Study TTL strategies..."]
          },
          "session_complete": False
        }
    """

    # ── 1. Load and validate session ──────────────────────────────
    session = db.get(InterviewSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    if session.status == SessionStatus.COMPLETED:
        raise ValueError(f"Session {session_id} is already completed")
    if session.question_count == 0:
        raise ValueError(
            f"Session {session_id} has not started yet. Call GET /api/session/{session_id}/start first"
        )

    print(f"\n📨 Message received for session {session_id}, Q{session.question_count}")

    # ── 2. Find the AI question that was just answered ────────────
    # We need it for EvaluationChain context and for saving to DB
    last_ai_question_msg = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.role == MessageRole.AI)
        .order_by(Message.id.desc())
    ).first()

    if not last_ai_question_msg:
        raise ValueError(
            f"No AI question found for session {session_id}. Start the session before sending answers"
        )

    last_ai_question = last_ai_question_msg.content
    current_q_number = session.question_count  # The question being answered NOW

    # ── 3. Run slow LLM tasks ─────────────────────────────────────
    # Evaluation and next-question generation are independent, so run them concurrently.
    print(f"   📊 Evaluating answer for Q{current_q_number}...")
    next_q_number = current_q_number + 1
    is_complete = next_q_number > session.max_questions

    evaluation_task = asyncio.create_task(
        _safe_evaluate_answer(
            question=last_ai_question,
            user_answer=user_answer,
            interview_type=session.interview_type,
        )
    )

    next_question = ""
    if not is_complete:
        print(f"   🤖 Generating Q{next_q_number}...")
        chain = _get_or_create_session_chain(session)
        history = get_history(session_id)[-4:]  # last 2 exchanges only for lower latency
        profile_context = _build_resume_profile_context(session, db)
        generation_input = user_answer
        if profile_context:
            generation_input = f"{user_answer}\n\n{profile_context}"
        prior_ai_questions = [
            msg.content
            for msg in db.exec(
                select(Message)
                .where(Message.session_id == session_id)
                .where(Message.role == MessageRole.AI)
                .order_by(Message.id)
            ).all()
            if msg.content
        ]
        next_question_task = asyncio.create_task(
            _safe_generate_question(
                chain=chain,
                payload={
                    "user_answer": generation_input,
                    "question_number": next_q_number,
                    "history": history,
                },
                interview_type=session.interview_type,
                question_number=next_q_number,
            )
        )
        evaluation_data, next_question = await asyncio.gather(evaluation_task, next_question_task)

        if _is_duplicate_question(next_question, prior_ai_questions):
            print("   ⚠️ Duplicate/near-duplicate question detected; retrying generation with anti-repeat steering")
            steer = (
                generation_input
                + "\n\n[Instruction: Ask a different next question than previous turns. "
                + "Do not repeat the same wording or topic.]"
            )
            retry_question = await _safe_generate_question(
                chain=chain,
                payload={
                    "user_answer": steer,
                    "question_number": next_q_number,
                    "history": history,
                },
                interview_type=session.interview_type,
                question_number=next_q_number,
            )

            if _is_duplicate_question(retry_question, prior_ai_questions):
                print("   ⚠️ Retry still repetitive; using diversified fallback question")
                next_question = _contextual_fallback_question(
                    session=session,
                    db=db,
                    question_number=next_q_number,
                    last_ai_question=last_ai_question,
                    user_answer=user_answer,
                )
            else:
                next_question = retry_question

        if not next_question or not next_question.strip():
            # Retriever/embedding path can timeout under network/rate-limit pressure.
            # Retry once with a lightweight no-retrieval chain but keep CV/profile context in input.
            print("   ⚠️ Full retrieval-based generation failed; trying lightweight no-retrieval generation")
            light_chain = _get_or_create_light_chain(session.interview_type)
            light_input = (
                generation_input
                + "\n\n[Instruction: Ask the next question based on the candidate profile and previous answer. "
                + "Do not repeat previous questions.]"
            )
            next_question = await _safe_generate_question(
                chain=light_chain,
                payload={
                    "user_answer": light_input,
                    "question_number": next_q_number,
                    "history": history,
                },
                interview_type=session.interview_type,
                question_number=next_q_number,
            )

        if not next_question or not next_question.strip():
            next_question = _contextual_fallback_question(
                session=session,
                db=db,
                question_number=next_q_number,
                last_ai_question=last_ai_question,
                user_answer=user_answer,
            )

        print(f"   ✅ Next question generated")
    else:
        evaluation_data = await evaluation_task
        next_question = (
            "That's the end of your interview! 🎉 "
            "Your full evaluation report is being generated. "
            "Click 'View Report' to see your detailed feedback."
        )

    print(f"   ✅ Evaluation complete: overall_score={evaluation_data.get('overall_score')}")

    # ── 4. Save user's answer to DB ───────────────────────────────
    user_msg = Message(
        session_id=session_id,
        role=MessageRole.USER,
        content=user_answer,
        question_number=current_q_number,
        ai_question_asked=last_ai_question,  # link answer to its question
    )
    db.add(user_msg)
    db.flush()  # flush = write to DB transaction without committing yet
                # We need user_msg.id for the Evaluation foreign key

    # ── 5. Save Evaluation to DB ──────────────────────────────────
    evaluation_row = Evaluation(
        session_id=session_id,
        message_id=user_msg.id,
        question_number=current_q_number,

        # Scores (0-10)
        technical_correctness=evaluation_data.get("technical_correctness", 5),
        depth_of_explanation=evaluation_data.get("depth_of_explanation", 5),
        clarity=evaluation_data.get("clarity", 5),
        overall_score=evaluation_data.get("overall_score", 5),

        # Qualitative feedback — stored as JSON strings in SQLite
        strengths=json.dumps(evaluation_data.get("strengths", [])),
        weaknesses=json.dumps(evaluation_data.get("weaknesses", [])),
        suggestions=json.dumps(evaluation_data.get("suggestions", [])),
    )
    db.add(evaluation_row)

    # ── 6. NEXT question is already prepared above ────────────────

    # ── 7. Save AI question to DB ─────────────────────────────────
    ai_msg = Message(
        session_id=session_id,
        role=MessageRole.AI,
        content=next_question,
        question_number=next_q_number if not is_complete else None,
    )
    db.add(ai_msg)

    # ── 8. Update conversation memory ─────────────────────────────
    save_exchange(session_id, user_answer, next_question)

    # ── 9. Finalize session state ─────────────────────────────────
    session.question_count = next_q_number if not is_complete else session.max_questions
    if is_complete:
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.utcnow()
        print(f"   🏁 Session {session_id} COMPLETED")

    db.add(session)
    db.commit()

    # Phase 4: eagerly generate report when session reaches completion.
    # We keep this non-fatal so interview completion never fails due to report issues.
    if is_complete:
        try:
            generate_or_get_report(session_id=session_id, db=db)
            print(f"   📊 Report generated for session {session_id}")
        except Exception as e:
            print(f"   ⚠️ Report generation failed for session {session_id}: {e}")
        finally:
            _session_question_chains.pop(session_id, None)

    # ── 10. Return response ───────────────────────────────────────
    return {
        "ai_question": next_question,
        "question_number": next_q_number if not is_complete else session.max_questions,
        "session_complete": is_complete,
        "evaluation": {
            "overall_score": evaluation_data.get("overall_score", 5),
            "technical_correctness": evaluation_data.get("technical_correctness", 5),
            "depth_of_explanation": evaluation_data.get("depth_of_explanation", 5),
            "clarity": evaluation_data.get("clarity", 5),
            "strengths": evaluation_data.get("strengths", []),
            "weaknesses": evaluation_data.get("weaknesses", []),
            "suggestions": evaluation_data.get("suggestions", []),
        },
    }


# ── Helper: Get Session History ────────────────────────────────────

def get_session_detail(session_id: int, db: Session) -> dict:
    """
    Get session with full message history.
    Frontend calls this on page load to restore a session.
    """
    session = db.get(InterviewSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    messages = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.id)
    ).all()

    return {
        "session_id": session.id,
        "interview_type": session.interview_type,
        "status": session.status,
        "question_count": session.question_count,
        "max_questions": session.max_questions,
        "created_at": session.created_at.isoformat(),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "question_number": msg.question_number,
            }
            for msg in messages
        ],
    }
