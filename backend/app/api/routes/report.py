"""routes/report.py — Phase 4 report generation and retrieval endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.api.error_utils import api_error
from app.db.database import get_db
from app.services import report_service

router = APIRouter()


class ReportResponse(BaseModel):
    report_id: int
    session_id: int
    interview_type: str
    overall_score: float
    per_question_scores: list[int]
    per_dimension_scores: dict[str, Any]
    top_strengths: list[str]
    top_weaknesses: list[str]
    suggestions: list[str]
    created_at: str


@router.get("/{session_id}")
def get_report(
    session_id: int,
  regenerate: bool = Query(
    default=False,
    description="Regenerate report from evaluations even if one already exists",
  ),
    db: Session = Depends(get_db),
):
    """
    Get a session report.

    Behavior:
    - If report already exists, return it
    - If not, generate it from Evaluation rows (Phase 4)
    - Optional regenerate=true forces recalculation
    """
    try:
      report = report_service.generate_or_get_report(
        session_id=session_id,
        db=db,
        force_regenerate=regenerate,
      )
      payload = report_service.serialize_report(report)
      return ReportResponse(**payload)
    except ValueError as e:
      detail = str(e)
      status_code = 404 if "not found" in detail.lower() else 400
      error_code = "REPORT_SESSION_NOT_FOUND" if status_code == 404 else "REPORT_INVALID_REQUEST"
      raise api_error(
          status_code=status_code,
          code=error_code,
          message=detail,
          context={"session_id": session_id},
      )
    except Exception as e:
      raise api_error(
          status_code=500,
          code="REPORT_GENERATION_FAILED",
          message=f"Failed to generate report: {str(e)}",
          context={"session_id": session_id},
      )
