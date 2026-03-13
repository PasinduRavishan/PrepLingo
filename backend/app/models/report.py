"""
models/report.py

WHY A SEPARATE REPORT MODEL:
  The Report is the final deliverable — what the user actually sees
  after the interview ends. It's a computed summary of all Evaluations.

  We store it separately (not just computed on-the-fly) because:
  1. Performance: don't re-calculate on every page load
  2. Permanence: user can come back and see old reports
  3. Shareable: easy to GET /report/{id} without re-processing

HOW IT'S GENERATED (see services/report_service.py):
  1. Fetch all Evaluation rows for this session_id
  2. Average the scores per dimension → per_dimension_scores
  3. Collect all strengths/weaknesses → find most common → top_strengths/top_weaknesses
  4. overall_score = average of all overall_score values → convert to percentage (×10)

per_question_scores JSON example:
  "[8, 6, 7, 5, 8, 7, 6, 8]"
  → 8 values for 8 questions
  → Used to draw the line chart on the report page

per_dimension_scores JSON example:
  '{"technical_correctness": 7.2, "depth_of_explanation": 6.5, "clarity": 8.1}'
  → Used to draw the radar chart on the report page
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: Optional[int] = Field(default=None, primary_key=True)

    # One report per session (unique constraint)
    session_id: int = Field(foreign_key="interview_sessions.id", unique=True)

    # Interview type (duplicated for easy display without JOIN)
    interview_type: str

    # 0-100 percentage — the headline score
    overall_score: float

    # JSON: scores for each of the 8 questions → line chart data
    per_question_scores: str = Field(default="[]")

    # JSON: average by dimension → radar chart data
    per_dimension_scores: str = Field(default="{}")

    # JSON: top 3 things the candidate did well
    top_strengths: str = Field(default="[]")

    # JSON: top 3 areas to improve
    top_weaknesses: str = Field(default="[]")

    # JSON: actionable study suggestions from the AI
    suggestions: str = Field(default="[]")

    created_at: datetime = Field(default_factory=datetime.utcnow)
