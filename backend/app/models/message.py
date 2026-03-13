"""
models/message.py

WHY WE STORE EVERY MESSAGE:
  The conversation between AI and user is the interview.
  By storing every message, we can:
  1. Rebuild conversation history for LangChain memory on reconnect
  2. Generate the report from actual Q&A pairs
  3. Let users replay/review past interviews (future feature)

MessageRole:
  "ai"   → The question asked by the AI interviewer
  "user" → The answer given by the candidate

question_number:
  Only set on AI messages. Tracks "this is question 3 of 8".
  Used to correlate AI questions with Evaluation scores in the report.

ai_question_asked:
  For USER messages, we store what AI question they were answering.
  This gives the Evaluation chain the full context:
  "Given this question: [X], the user answered: [Y]"
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class MessageRole(str, Enum):
    AI = "ai"
    USER = "user"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Which session this message belongs to
    session_id: int = Field(foreign_key="interview_sessions.id", index=True)

    # Who sent the message
    role: MessageRole

    # The actual text content (question or answer)
    content: str

    # For AI messages: which question number this is (1-8)
    question_number: Optional[int] = Field(default=None)

    # For USER messages: what question the AI had asked
    # Stored so EvaluationChain has the question+answer pair
    ai_question_asked: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
