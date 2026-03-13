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

import json
from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.models.session import InterviewSession, SessionStatus
from app.models.message import Message, MessageRole
from app.models.evaluation import Evaluation
from app.langchain_layer.retrievers.dual_retriever import build_dual_retriever, format_retrieved_docs
from app.langchain_layer.chains.question_chain import build_question_chain
from app.langchain_layer.chains.evaluation_chain import evaluate_answer
from app.langchain_layer.memory.session_memory import get_or_create_memory, save_exchange, get_history
from app.langchain_layer.prompts import get_prompt_for_type


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
    seed_input = "start introduction background experience"

    # Build retriever using the session's guest_id + interview type
    retriever = build_dual_retriever(
        guest_id=session.guest_id,
        interview_type=session.interview_type,
    )

    # Get the right prompt template for this interview type
    prompt = get_prompt_for_type(session.interview_type)

    # Build the LCEL question chain
    chain = build_question_chain(retriever, prompt)

    print(f"🤖 Generating opening question for session {session.id}...")
    first_question = await chain.ainvoke({
        "user_answer": seed_input,
        "question_number": 1,
        "history": [],  # Empty at start
    })

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

    print(f"\n📨 Message received for session {session_id}, Q{session.question_count}")

    # ── 2. Find the AI question that was just answered ────────────
    # We need it for EvaluationChain context and for saving to DB
    last_ai_question_msg = db.exec(
        select(Message)
        .where(Message.session_id == session_id)
        .where(Message.role == MessageRole.AI)
        .order_by(Message.id.desc())
    ).first()

    last_ai_question = last_ai_question_msg.content if last_ai_question_msg else ""
    current_q_number = session.question_count  # The question being answered NOW

    # ── 3. Run EvaluationChain on the user's answer ───────────────
    # We get some basic context for the evaluator from the retriever
    # (the same context the question was generated from)
    print(f"   📊 Evaluating answer for Q{current_q_number}...")
    evaluation_data = await evaluate_answer(
        question=last_ai_question,
        user_answer=user_answer,
        context=last_ai_question,  # Use the question itself as minimal context
        interview_type=session.interview_type,
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

    # ── 6. Generate NEXT question (if session not complete) ───────
    next_q_number = current_q_number + 1
    is_complete = next_q_number > session.max_questions

    next_question = ""
    if not is_complete:
        print(f"   🤖 Generating Q{next_q_number}...")

        # Build dual retriever: user's resume + domain knowledge
        retriever = build_dual_retriever(
            guest_id=session.guest_id,
            interview_type=session.interview_type,
        )

        # Get interview-type-specific prompt
        prompt = get_prompt_for_type(session.interview_type)

        # Build LCEL chain and invoke
        chain = build_question_chain(retriever, prompt)
        history = get_history(session_id)   # Last 6 exchanges from memory

        next_question = await chain.ainvoke({
            "user_answer": user_answer,
            "question_number": next_q_number,
            "history": history,
        })
        print(f"   ✅ Next question generated")

    else:
        # Interview is done — this was the final answer
        next_question = (
            "That's the end of your interview! 🎉 "
            "Your full evaluation report is being generated. "
            "Click 'View Report' to see your detailed feedback."
        )

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
