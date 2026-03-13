"""
models/resume.py

WHY WE STORE BOTH raw_text AND parsed_data:

  raw_text:
    The full extracted text from the PDF. We store this so we can:
    - Re-parse if we improve the parsing prompt later
    - Chunk it for the ChromaDB vector store (the RAG part)

  parsed_data (JSON string):
    The structured extraction from Gemini — skills, projects, etc.
    We could use a separate table with foreign keys for each skill,
    but storing as JSON is simpler and flexible at this stage.

    Example stored value:
    {
      "name": "Ravi Sharma",
      "skills": ["Python", "React", "MongoDB"],
      "projects": [
        {
          "name": "Blockchain Supply Chain",
          "description": "Tracking system using Hyperledger Fabric",
          "tech_stack": ["Hyperledger Fabric", "Docker", "Node.js"],
          "outcomes": "Reduced tracking errors by 30%"
        }
      ],
      "experience": [...],
      "education": [...]
    }

  chunks_embedded:
    A flag so we know whether this resume's text has been split
    and stored in the ChromaDB vector store yet.
    After embedding, we set this to True.
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Resume(SQLModel, table=True):
    __tablename__ = "resumes"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Links resume to the right guest user
    guest_id: str = Field(index=True)

    # Raw extracted text from PyMuPDF — the full PDF content
    raw_text: str

    # Structured JSON extracted by Gemini
    # Stored as string because SQLite doesn't have a native JSON column
    parsed_data: str = Field(default="{}")

    # Tracks whether this resume has been embedded into ChromaDB
    chunks_embedded: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
