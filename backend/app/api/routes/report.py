"""
routes/report.py — Report Endpoints

WHAT A REPORT CONTAINS:
  After the interview (8 questions), the backend computes a final report:
  
  - overall_score: 0-100 percentage
  - per_question_scores: [8, 6, 7, 5, 8, 7, 6, 8] — line chart
  - per_dimension_scores: {technical: 7.2, clarity: 8.1, ...} — radar chart
  - top_strengths: ["Clear explanations", "Good examples"]
  - top_weaknesses: ["Missed caching", "Vague on scaling"]
  - suggestions: ["Study cache-aside pattern", "Read about CDN"]

ENDPOINTS:
  GET /api/report/{session_id} — Get the report for a session
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.database import get_db

router = APIRouter()


@router.get("/{session_id}")
def get_report(
    session_id: int,
    db: Session = Depends(get_db),
):
    """
    Get the final interview report.
    
    Phase 6 implementation:
    - Fetch all Evaluation rows for this session
    - Calculate averages per dimension
    - Find top-3 most mentioned strengths/weaknesses
    - Build and return Report object
    """
    # TODO: Phase 6
    return {
        "session_id": session_id,
        "overall_score": 0,
        "per_question_scores": [],
        "per_dimension_scores": {},
        "top_strengths": [],
        "top_weaknesses": [],
        "suggestions": [],
        "message": "Report generation coming in Phase 6.",
    }
