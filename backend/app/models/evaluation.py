"""
models/evaluation.py

WHY STORE SCORES AS SEPARATE FIELDS (not JSON):
  We store each score dimension in its own column so we can:
  - Calculate averages per dimension in SQL: AVG(technical_correctness)
  - Build the radar chart data on the report page efficiently
  - Filter sessions by score later (e.g., "show me sessions where clarity < 5")

  strengths / weaknesses / suggestions are stored as JSON strings
  because they're lists and vary in length. SQLite doesn't have array columns.

SCORE SCALE: 0-10
  - 0-3: Poor — major gaps
  - 4-5: Below average — needs work
  - 6-7: Average — acceptable but improvable
  - 8-9: Good — solid answer
  - 10:  Excellent — outstanding

CRITERIA BY INTERVIEW TYPE:
  All types use: technical_correctness, depth, clarity, overall
  System Design also weights: architecture_thinking
  Behavioral weights: communication_clarity over technical_correctness
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Evaluation(SQLModel, table=True):
    __tablename__ = "evaluations"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Which session this evaluation belongs to
    session_id: int = Field(foreign_key="interview_sessions.id", index=True)

    # Which user message was evaluated (the answer message)
    message_id: int = Field(foreign_key="messages.id")

    # Which question number (1-8) in the session
    question_number: int

    # --- Score Dimensions (0-10 each) ---

    # Is the answer factually correct?
    technical_correctness: int = Field(default=0)

    # Did they explain deeply enough? Or surface-level?
    depth_of_explanation: int = Field(default=0)

    # Was it clear and well-structured?
    clarity: int = Field(default=0)

    # Weighted average of the above (computed by EvaluationChain)
    overall_score: int = Field(default=0)

    # --- Qualitative Feedback (stored as JSON strings) ---

    # e.g. '["Clearly explained load balancing", "Good use of examples"]'
    strengths: str = Field(default="[]")

    # e.g. '["Missed caching strategies", "No mention of CDN"]'
    weaknesses: str = Field(default="[]")

    # e.g. '["Read about cache-aside pattern", "Study CDN usage"]'
    suggestions: str = Field(default="[]")

    created_at: datetime = Field(default_factory=datetime.utcnow)
