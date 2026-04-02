"""
services/report_service.py

Phase 4 report generation service.

Responsibilities:
1. Validate session state for report generation
2. Aggregate per-question and per-dimension scores from Evaluation rows
3. Extract top strengths/weaknesses/suggestions from qualitative feedback
4. Persist one Report row per session (idempotent)
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from sqlmodel import Session, select

from app.models.evaluation import Evaluation
from app.models.report import Report
from app.models.session import InterviewSession, SessionStatus


def _is_session_completed(status: Any) -> bool:
    """Handle enum/string variants from ORM serialization safely."""
    if status is None:
        return False
    as_text = str(status).strip().lower()
    return as_text in {
        SessionStatus.COMPLETED.value.lower(),
        SessionStatus.COMPLETED.name.lower(),
    } or as_text.endswith(".completed")


def _safe_json_list(value: str | None) -> list[str]:
    """Parse a JSON array string safely, returning [] on bad input."""
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return []
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _round2(value: float) -> float:
    """Round to 2 decimals for stable API/UI values."""
    return round(float(value), 2)


def _build_report_payload(evaluations: list[Evaluation]) -> dict[str, Any]:
    """Compute report payload from a list of evaluations."""
    per_question_scores = [e.overall_score for e in sorted(evaluations, key=lambda x: x.question_number)]

    count = len(evaluations)
    technical_avg = sum(e.technical_correctness for e in evaluations) / count
    depth_avg = sum(e.depth_of_explanation for e in evaluations) / count
    clarity_avg = sum(e.clarity for e in evaluations) / count
    overall_avg_10 = sum(e.overall_score for e in evaluations) / count

    strengths_counter: Counter[str] = Counter()
    weaknesses_counter: Counter[str] = Counter()
    suggestions_counter: Counter[str] = Counter()

    for e in evaluations:
        strengths_counter.update(_safe_json_list(e.strengths))
        weaknesses_counter.update(_safe_json_list(e.weaknesses))
        suggestions_counter.update(_safe_json_list(e.suggestions))

    return {
        "overall_score": _round2(overall_avg_10 * 10),  # 0-100 scale
        "per_question_scores": per_question_scores,
        "per_dimension_scores": {
            "technical_correctness": _round2(technical_avg),
            "depth_of_explanation": _round2(depth_avg),
            "clarity": _round2(clarity_avg),
            "overall": _round2(overall_avg_10),
        },
        "top_strengths": [text for text, _ in strengths_counter.most_common(3)],
        "top_weaknesses": [text for text, _ in weaknesses_counter.most_common(3)],
        "suggestions": [text for text, _ in suggestions_counter.most_common(5)],
    }


def generate_or_get_report(session_id: int, db: Session, force_regenerate: bool = False) -> Report:
    """
    Generate and persist a report for a completed session, or return existing one.

    Raises:
        ValueError: on missing session, incomplete session, or missing evaluations.
    """
    session = db.get(InterviewSession, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    if not _is_session_completed(session.status):
        raise ValueError("Report is only available after session completion")

    existing_report = db.exec(
        select(Report).where(Report.session_id == session_id)
    ).first()
    if existing_report and not force_regenerate:
        return existing_report

    evaluations = db.exec(
        select(Evaluation)
        .where(Evaluation.session_id == session_id)
        .order_by(Evaluation.question_number)
    ).all()

    if not evaluations:
        raise ValueError("No evaluations found for this session")

    payload = _build_report_payload(evaluations)

    if existing_report:
        report = existing_report
    else:
        report = Report(
            session_id=session_id,
            interview_type=str(session.interview_type),
            overall_score=0.0,
        )

    report.interview_type = str(session.interview_type)
    report.overall_score = payload["overall_score"]
    report.per_question_scores = json.dumps(payload["per_question_scores"])
    report.per_dimension_scores = json.dumps(payload["per_dimension_scores"])
    report.top_strengths = json.dumps(payload["top_strengths"])
    report.top_weaknesses = json.dumps(payload["top_weaknesses"])
    report.suggestions = json.dumps(payload["suggestions"])

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def serialize_report(report: Report) -> dict[str, Any]:
    """Convert Report row (JSON text columns) to API-ready dict."""
    try:
        parsed_questions = json.loads(report.per_question_scores or "[]")
        if not isinstance(parsed_questions, list):
            parsed_questions = []
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed_questions = []

    clean_question_scores: list[int] = []
    for score in parsed_questions:
        try:
            clean_question_scores.append(int(score))
        except (TypeError, ValueError):
            continue

    try:
        per_dimension_scores = json.loads(report.per_dimension_scores or "{}")
        if not isinstance(per_dimension_scores, dict):
            per_dimension_scores = {}
    except (TypeError, ValueError, json.JSONDecodeError):
        per_dimension_scores = {}

    return {
        "session_id": report.session_id,
        "interview_type": report.interview_type,
        "overall_score": report.overall_score,
        "per_question_scores": clean_question_scores,
        "per_dimension_scores": per_dimension_scores,
        "top_strengths": _safe_json_list(report.top_strengths),
        "top_weaknesses": _safe_json_list(report.top_weaknesses),
        "suggestions": _safe_json_list(report.suggestions),
        "report_id": report.id,
        "created_at": report.created_at.isoformat(),
    }
