"""
routes/session.py — Interview Session Endpoints (Phase 3 — FULLY IMPLEMENTED)

ENDPOINTS:
  POST /api/session/                    → Create session
  GET  /api/session/{id}/start          → Get first question (no answer needed)
  GET  /api/session/{id}                → Get session detail + message history
  POST /api/session/{id}/message        → Send answer → get next question + evaluation
  POST /api/session/{id}/end            → Manually end session

THE FLOW (for frontend to follow):
  1. POST /api/session/          with {guest_id, interview_type, resume_id}
     → Returns {session_id, ...}

  2. GET /api/session/{id}/start
     → Returns {ai_question: "Hi! I'm your technical interviewer. Tell me about..."}

  3. Repeat until session_complete=True:
     POST /api/session/{id}/message  with {content: "My answer..."}
     → Returns {ai_question: "Next question...", evaluation: {...}, question_number: N}

  4. When session_complete=True → navigate to /report page
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session
from pydantic import BaseModel
from typing import Optional

from app.api.error_utils import api_error
from app.db.database import get_db
from app.models.resume import Resume
from app.models.session import InterviewType
from app.services import session_service

router = APIRouter()


# ── Request / Response Schemas ────────────────────────────────────

class CreateSessionRequest(BaseModel):
    guest_id: str
    interview_type: InterviewType
    resume_id: Optional[int] = None


class CreateSessionResponse(BaseModel):
    session_id: int
    interview_type: str
    status: str
    max_questions: int
    message: str


class SendMessageRequest(BaseModel):
    content: str  # The user's answer text


class EvaluationResult(BaseModel):
    overall_score: int
    technical_correctness: int
    depth_of_explanation: int
    clarity: int
    strengths: list
    weaknesses: list
    suggestions: list


class SendMessageResponse(BaseModel):
    ai_question: str
    evaluation: Optional[EvaluationResult]
    question_number: int
    session_complete: bool


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/", response_model=CreateSessionResponse)
def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
):
    """
    Create a new interview session (synchronous — just writes to DB).

    After this call, use GET /api/session/{id}/start to get the first question.

    WHY SEPARATE create + start?
      create = fast, synchronous DB write
      start  = slow, async Groq LLM call
      
      Separation means the session is DB-persisted even if Groq is slow.
      Frontend can show a "Session created!" state while waiting for start.

    For RESUME interview type:
      Ideally a resume_id should be provided so the AI can personalize
      questions based on the candidate's actual projects and skills.
    """
    if not request.guest_id or not request.guest_id.strip():
        raise api_error(status_code=400, code="MISSING_GUEST_ID", message="guest_id is required")

    if request.interview_type == InterviewType.RESUME and request.resume_id is None:
        raise api_error(
            status_code=400,
            code="MISSING_RESUME_ID",
            message="resume_id is required for resume interview type",
        )

    if request.resume_id is not None:
        resume = db.get(Resume, request.resume_id)
        if not resume:
            raise api_error(
                status_code=404,
                code="RESUME_NOT_FOUND",
                message=f"Resume {request.resume_id} not found",
                context={"resume_id": request.resume_id},
            )
        if resume.guest_id != request.guest_id:
            raise api_error(
                status_code=403,
                code="RESUME_GUEST_MISMATCH",
                message="resume_id does not belong to the provided guest_id",
                context={"resume_id": request.resume_id, "guest_id": request.guest_id},
            )

    try:
        session = session_service.create_session(
            guest_id=request.guest_id.strip(),
            interview_type=request.interview_type.value,
            resume_id=request.resume_id,
            db=db,
        )
        return CreateSessionResponse(
            session_id=session.id,
            interview_type=session.interview_type,
            status=session.status,
            max_questions=session.max_questions,
            message=(
                f"Session created! Type: {session.interview_type}. "
                f"Now call GET /api/session/{session.id}/start to get your first question."
            ),
        )
    except Exception as e:
        raise api_error(
            status_code=500,
            code="SESSION_CREATE_FAILED",
            message=f"Failed to create session: {str(e)}",
        )


@router.get("/{session_id}/start")
async def start_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Generate the FIRST question for a session.

    This is an async GET endpoint because it calls Groq to generate
    the opening question. It uses the interview type and the candidate's
    resume (via ChromaDB) to start a personalized question.

    Only works if session.question_count == 0.
    Calling it twice returns an error (session already started).
    """
    from app.models.session import InterviewSession
    session = db.get(InterviewSession, session_id)

    if not session:
        raise api_error(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Session {session_id} not found",
            context={"session_id": session_id},
        )

    if session.question_count > 0:
        raise api_error(
            status_code=400,
            code="SESSION_ALREADY_STARTED",
            message="Session already started. Use POST /message to continue.",
        )

    try:
        result = await session_service.get_first_question(session=session, db=db)
        return result
    except Exception as e:
        raise api_error(
            status_code=500,
            code="FIRST_QUESTION_FAILED",
            message=f"Failed to generate first question: {str(e)}",
        )


@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get session detail and full message history.
    Frontend calls this on page load to restore a session in progress.
    """
    try:
        return session_service.get_session_detail(session_id=session_id, db=db)
    except ValueError as e:
        raise api_error(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=str(e),
            context={"session_id": session_id},
        )


@router.post("/{session_id}/message", response_model=SendMessageResponse)
async def send_message(
    session_id: int,
    request: SendMessageRequest,
    db: Session = Depends(get_db),
):
    """
    THE CORE ENDPOINT — The AI interview loop.

    User sends their answer → Full LangChain pipeline runs →
    Returns AI's next question + structured evaluation of the answer.

    Pipeline (in order):
    1. EvaluationChain  → scores user's answer with Groq (0-10 per dimension)
    2. QuestionChain    → uses DualRetriever + Groq → generates next question
    3. SessionMemory    → saves exchange for context in future turns
    4. DB write         → persists everything

    This is async because Groq LLM calls are I/O-bound network operations.
    FastAPI can handle other requests while waiting for Groq to respond!
    """
    if not request.content or not request.content.strip():
        raise api_error(
            status_code=400,
            code="EMPTY_ANSWER",
            message="Answer content cannot be empty",
        )

    try:
        result = await session_service.process_message(
            session_id=session_id,
            user_answer=request.content.strip(),
            db=db,
        )
        return SendMessageResponse(
            ai_question=result["ai_question"],
            question_number=result["question_number"],
            session_complete=result["session_complete"],
            evaluation=EvaluationResult(**result["evaluation"]) if result.get("evaluation") else None,
        )
    except ValueError as e:
        raise api_error(
            status_code=400,
            code="SESSION_MESSAGE_INVALID",
            message=str(e),
            context={"session_id": session_id},
        )
    except Exception as e:
        raise api_error(
            status_code=500,
            code="SESSION_PIPELINE_ERROR",
            message=f"Interview pipeline error: {str(e)}",
            context={"session_id": session_id},
        )


@router.post("/{session_id}/end")
def end_session(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Manually end a session (e.g., user quits early).
    Frontend can use this if the user clicks "End Interview" before 8 questions.
    Report generation happens in Phase 4.
    """
    from app.models.session import InterviewSession, SessionStatus
    from app.services.report_service import generate_or_get_report
    from datetime import datetime

    session = db.get(InterviewSession, session_id)
    if not session:
        raise api_error(
            status_code=404,
            code="SESSION_NOT_FOUND",
            message=f"Session {session_id} not found",
            context={"session_id": session_id},
        )

    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.utcnow()
    db.add(session)
    db.commit()

    report_message = "Session ended."
    try:
        generate_or_get_report(session_id=session_id, db=db)
        report_message = "Session ended and report generated."
    except Exception as e:
        report_message = f"Session ended. Report not generated yet: {str(e)}"

    return {
        "session_id": session_id,
        "status": "completed",
        "message": report_message,
    }
