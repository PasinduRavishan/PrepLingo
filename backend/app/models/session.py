"""
models/session.py

WHY ENUMS FOR interview_type AND status:
  Using Python Enum + str inheritance (str, Enum) gives us:
  1. String stored in the database ("technical", "behavioral")
  2. Python type safety — only valid values accepted
  3. FastAPI auto-validates and documents these as dropdown choices
  4. Easy comparison: session.status == SessionStatus.IN_PROGRESS

SESSION LIFECYCLE:
  IN_PROGRESS → user is in the interview
  COMPLETED   → user finished or hit 8 questions
  ABANDONED   → user closed browser mid-session (future)

HOW question_count CONTROLS THE INTERVIEW:
  Every time the user sends a message:
    - We check question_count < max_questions
    - Increment question_count
    - If reached max → auto-complete session → trigger report

RESUME LINK (resume_id):
  Optional because:
  - Technical/Behavioral interviews can work without a resume
  - User might want to practice without uploading
  - Resume-Based mode requires it (validated in the route)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class InterviewType(str, Enum):
    RESUME = "resume"                   # Deep-dive into CV projects
    TECHNICAL = "technical"             # CS concepts + engineering
    SYSTEM_DESIGN = "system_design"     # Architecture + scalability
    BEHAVIORAL = "behavioral"           # STAR method + soft skills


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Which guest user owns this session
    guest_id: str = Field(index=True)

    # Which of the 4 interview types
    interview_type: InterviewType

    # Lifecycle state of this session
    status: SessionStatus = Field(default=SessionStatus.IN_PROGRESS)

    # How many questions have been asked so far
    question_count: int = Field(default=0)

    # Maximum questions before session auto-completes (default: 8)
    max_questions: int = Field(default=8)

    # Optional resume link — required for RESUME type, optional for others
    resume_id: Optional[int] = Field(default=None, foreign_key="resumes.id")

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Set when session is completed
    ended_at: Optional[datetime] = Field(default=None)
