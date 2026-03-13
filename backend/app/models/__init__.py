"""
models/__init__.py

CRITICAL — This file must import ALL models.

WHY: SQLModel uses SQLAlchemy under the hood, which maintains a "metadata"
registry of all table definitions. When create_tables() calls
SQLModel.metadata.create_all(engine), it only creates tables it KNOWS about.

If a model file is never imported, that table NEVER gets created.
By importing everything here, and importing this module in database.py,
we guarantee all tables are registered before create_all() runs.
"""

from app.models.user import GuestUser
from app.models.resume import Resume
from app.models.session import InterviewSession, InterviewType, SessionStatus
from app.models.message import Message, MessageRole
from app.models.evaluation import Evaluation
from app.models.report import Report

__all__ = [
    "GuestUser",
    "Resume",
    "InterviewSession",
    "InterviewType",
    "SessionStatus",
    "Message",
    "MessageRole",
    "Evaluation",
    "Report",
]
