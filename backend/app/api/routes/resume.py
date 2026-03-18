"""
routes/resume.py — Resume Upload & Parsing Endpoints (Phase 2 — IMPLEMENTED)

ENDPOINTS:
  POST /api/resume/upload  — Upload PDF, extract, parse with Gemini, embed in RAG
  GET  /api/resume/{id}    — Get parsed resume data
"""

import json
from fastapi import APIRouter, File, UploadFile, Depends, Query, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import Optional

from app.api.error_utils import api_error
from app.db.database import get_db, engine
from app.models.resume import Resume
from app.services import resume_service

router = APIRouter()


def _embed_resume_background(resume_id: int, guest_id: str, raw_text: str, parsed_data: dict | None = None):
    """Run resume embedding out-of-band so upload response is fast."""
    try:
        num_chunks = resume_service.embed_resume_for_rag(
            guest_id=guest_id,
            raw_text=raw_text,
            parsed_data=parsed_data,
        )
        with Session(engine) as bg_db:
            resume_service.mark_resume_embedded(resume_id, bg_db)
        print(f"   ✅ Background embedding complete for resume_id={resume_id}, chunks={num_chunks}")
    except Exception as e:
        # Keep this non-fatal; resume remains usable and can be re-embedded later.
        print(f"   ⚠️ Background embedding failed for resume_id={resume_id}: {e}")


# ── Response Schemas ──────────────────────────────────────────────

class ProjectInfo(BaseModel):
    name: str
    description: str = ""
    tech_stack: list = []
    outcomes: str = ""


class ResumeUploadResponse(BaseModel):
    resume_id: int
    guest_id: str
    name: str
    parsed_skills: list
    parsed_projects: list
    chunks_embedded: int
    message: str


class ResumeGetResponse(BaseModel):
    resume_id: int
    guest_id: str
    name: str
    skills: list
    projects: list
    experience: list
    education: list
    chunks_embedded: bool


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF resume file"),
    guest_id: str = Query(..., description="Guest UUID from browser localStorage"),
    db: Session = Depends(get_db),
):
    """
    Upload and process a PDF resume.

    Full pipeline:
    1. Validate file is PDF
    2. Extract text with PyMuPDF
    3. Parse structured data with Gemini (LangChain chain)
    4. Save raw + parsed data to SQLite
    5. Chunk + embed into ChromaDB for RAG retrieval
    6. Return parsed summary to frontend

    The resume becomes available to the RAG system immediately after upload.
    When the user starts an interview, their resume chunks are retrieved
    alongside domain knowledge to personalize questions.
    """

    # ── Step 1: Validate ─────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise api_error(
            status_code=400,
            code="INVALID_FILE_TYPE",
            message="Only PDF files are accepted. Please upload a .pdf resume.",
            context={"expected_extension": ".pdf", "filename": file.filename or ""},
        )

    if not guest_id or guest_id.strip() == "":
        raise api_error(
            status_code=400,
            code="MISSING_GUEST_ID",
            message="guest_id is required. Generate a UUID in your browser.",
        )

    # ── Step 2: Extract text from PDF ────────────────────────────
    print(f"📄 Extracting text from PDF: {file.filename}")
    file_bytes = await file.read()

    try:
        raw_text = resume_service.extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise api_error(
            status_code=422,
            code="RESUME_PARSE_ERROR",
            message=str(e),
        )

    print(f"   ✅ Extracted {len(raw_text)} characters from PDF")

    # ── Step 3: Parse with Gemini LLM ────────────────────────────
    print("🤖 Parsing resume with Gemini (LangChain chain)...")
    parsed_data = await resume_service.parse_resume_with_llm(raw_text)
    print(f"   ✅ Extracted {len(parsed_data.get('skills', []))} skills, "
          f"{len(parsed_data.get('projects', []))} projects")

    # ── Step 4: Save to SQLite ────────────────────────────────────
    print("💾 Saving to database...")
    resume = resume_service.save_resume_to_db(
        guest_id=guest_id,
        raw_text=raw_text,
        parsed_data=parsed_data,
        db=db,
    )
    print(f"   ✅ Resume saved with ID: {resume.id}")

    # ── Step 5: Queue embedding (non-blocking) ───────────────────
    print("🔢 Queueing background resume embedding...")
    background_tasks.add_task(_embed_resume_background, resume.id, guest_id, raw_text, parsed_data)
    num_chunks = 0

    # ── Step 6: Return summary ────────────────────────────────────
    return ResumeUploadResponse(
        resume_id=resume.id,
        guest_id=guest_id,
        name=parsed_data.get("name", "Unknown"),
        parsed_skills=parsed_data.get("skills", []),
        parsed_projects=parsed_data.get("projects", []),
        chunks_embedded=num_chunks,
        message=(
            f"Resume processed successfully! "
            f"Found {len(parsed_data.get('skills', []))} skills and "
            f"{len(parsed_data.get('projects', []))} projects. "
            f"Embedding has started in the background and will complete shortly."
        ),
    )


@router.get("/{resume_id}/status")
def get_resume_embedding_status(
    resume_id: int,
    db: Session = Depends(get_db),
):
    """
    Lightweight endpoint for polling CV embedding status.
    Returns only chunks_embedded flag — much faster than the full resume GET.
    Frontend polls this after upload until chunks_embedded=true.
    """
    resume = db.get(Resume, resume_id)
    if not resume:
        raise api_error(
            status_code=404,
            code="RESUME_NOT_FOUND",
            message=f"Resume {resume_id} not found.",
        )
    return {"resume_id": resume_id, "chunks_embedded": resume.chunks_embedded}


@router.get("/{resume_id}", response_model=ResumeGetResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve parsed resume data by ID.
    Frontend uses this to show the user their parsed skills after upload.
    """
    resume = db.get(Resume, resume_id)

    if not resume:
        raise api_error(
            status_code=404,
            code="RESUME_NOT_FOUND",
            message=f"Resume {resume_id} not found.",
            context={"resume_id": resume_id},
        )

    parsed = json.loads(resume.parsed_data) if resume.parsed_data else {}

    return ResumeGetResponse(
        resume_id=resume.id,
        guest_id=resume.guest_id,
        name=parsed.get("name", ""),
        skills=parsed.get("skills", []),
        projects=parsed.get("projects", []),
        experience=parsed.get("experience", []),
        education=parsed.get("education", []),
        chunks_embedded=resume.chunks_embedded,
    )


@router.get("/guest/{guest_id}", response_model=Optional[ResumeGetResponse])
def get_resume_by_guest(
    guest_id: str,
    db: Session = Depends(get_db),
):
    """
    Get the most recent resume for a guest ID.
    Frontend calls this on dashboard load to check if user already has a resume.
    """
    resume = db.exec(
        select(Resume)
        .where(Resume.guest_id == guest_id)
        .order_by(Resume.id.desc())
    ).first()

    if not resume:
        return None

    parsed = json.loads(resume.parsed_data) if resume.parsed_data else {}

    return ResumeGetResponse(
        resume_id=resume.id,
        guest_id=resume.guest_id,
        name=parsed.get("name", ""),
        skills=parsed.get("skills", []),
        projects=parsed.get("projects", []),
        experience=parsed.get("experience", []),
        education=parsed.get("education", []),
        chunks_embedded=resume.chunks_embedded,
    )
