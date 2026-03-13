"""
services/resume_service.py — Resume Upload Pipeline

WHAT THIS FILE DOES:
  Implements the full resume processing pipeline in 4 steps:

  Step 1: extract_text_from_pdf(bytes) → str
    - Uses PyMuPDF (fitz) to pull raw text from the PDF
    - Fast, works on all PDF types

  Step 2: parse_resume_with_llm(text) → dict
    - Sends raw text to Gemini with a structured extraction prompt
    - Gets back clean JSON: {name, skills, projects, experience, education}
    - This IS a LangChain chain: PromptTemplate | LLM | JsonOutputParser

  Step 3: save_resume_to_db(guest_id, raw_text, parsed, db) → Resume
    - Persists the Resume row to SQLite
    - Stores both raw_text (for re-parsing later) and parsed_data (JSON)

  Step 4: embed_resume_for_rag(guest_id, raw_text) → int
    - Splits raw_text into chunks
    - Tags each chunk with: {guest_id, source: "resume", interview_type: "resume"}
    - Embeds via Google text-embedding-004 → stores in ChromaDB "resumes" collection
    - Returns number of chunks stored

WHY FOUR SEPARATE STEPS?
  Each step has a distinct concern and can fail independently.
  If Gemini parsing fails, we still have the raw text saved.
  If ChromaDB fails, the resume is still in the DB.
  Clear separation makes debugging much easier.
"""

import fitz  # PyMuPDF — PDF text extraction
import json
from typing import Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.models.resume import Resume
from app.langchain_layer.vector_store.store_manager import get_resume_store

settings = get_settings()


# ── Step 1: PDF Text Extraction ───────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract all text from a PDF file.

    WHY PyMuPDF (fitz)?
      - Fastest Python PDF library available
      - Handles both text-based and scan-based PDFs
      - Can extract metadata, images too (we only need text here)

    HOW IT WORKS:
      PDF documents have "pages". fitz opens the stream (bytes in memory,
      no temp file needed), then iterates each page calling get_text().
      The text is joined page-by-page.

    Args:
        file_bytes: Raw bytes of the uploaded PDF file

    Returns:
        Full extracted text as a single string

    Raises:
        ValueError: If PDF is corrupted or empty
    """
    try:
        # Open from bytes (no temp file needed — efficient)
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        pages_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            if page_text.strip():
                pages_text.append(page_text)

        doc.close()
        full_text = "\n\n".join(pages_text).strip()

        if not full_text:
            raise ValueError("PDF appears empty — no text could be extracted.")

        return full_text

    except Exception as e:
        raise ValueError(f"Failed to extract PDF text: {str(e)}")


# ── Step 2: LLM-Based Structured Extraction ───────────────────────

class ParsedResume(BaseModel):
    """
    The structured output we want from Gemini.

    WHY Pydantic here?
      JsonOutputParser uses this Pydantic class to:
      1. Auto-generate "format instructions" telling Gemini what JSON to produce
      2. Validate the LLM's response matches our expected structure

    The Pydantic model defines the CONTRACT between us and the LLM.
    """
    name: str
    skills: list         # ["Python", "React", "MongoDB"]
    projects: list       # [{"name": "...", "description": "...", "tech_stack": [...]}]
    experience: list     # [{"role": "...", "company": "...", "duration": "..."}]
    education: list      # [{"degree": "...", "institution": "...", "year": "..."}]


RESUME_PARSE_PROMPT = """You are an expert resume parser. Extract structured information 
from the resume text below. Be thorough and accurate.

Resume text:
{resume_text}

Instructions:
- skills: Extract ALL technical skills, programming languages, frameworks, tools, and technologies
- projects: For each project include name, description, tech_stack (list of technologies used), and outcomes
- experience: For each job include role, company, duration, and a brief description
- education: For each degree include degree name, institution, and year
- If a field is not found, use an empty list []

{format_instructions}

Return ONLY the JSON object. No explanation, no markdown code blocks.
"""


async def parse_resume_with_llm(raw_text: str) -> dict:
    """
    Use Gemini to extract structured data from resume text.

    THIS IS A LANGCHAIN CHAIN:
      PromptTemplate → ChatGroq → JsonOutputParser

    WHAT JsonOutputParser DOES BEHIND THE SCENES:
      1. Calls parser.get_format_instructions() → generates a JSON schema description
      2. That schema is injected into the prompt as {format_instructions}
      3. Groq reads it and returns JSON matching the schema
      4. Parser calls json.loads() on the response text
      5. Returns a Python dict
      
    WHY temperature=0.0?
      For data extraction, we want DETERMINISTIC output.
      Higher temperature → more creative → might invent skills or experiences.
      0.0 = always the same extraction for the same input.

    Returns:
        dict matching ParsedResume schema
    """
    parser = JsonOutputParser(pydantic_object=ParsedResume)

    prompt = PromptTemplate(
        template=RESUME_PARSE_PROMPT,
        input_variables=["resume_text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    llm = ChatGroq(
        model=settings.groq_model,
        groq_api_key=settings.groq_api_key,
        temperature=0.0,  # Deterministic for data extraction
    )

    # LCEL chain: prompt → llm → json parser
    # ainvoke = async invoke (non-blocking — doesn't hold up the server)
    chain = prompt | llm | parser

    try:
        result = await chain.ainvoke({"resume_text": raw_text})
        return result
    except Exception as e:
        # Fallback: return minimal structure if Groq parsing fails
        print(f"⚠️ LLM resume parsing failed: {e}")
        return {
            "name": "Unknown",
            "skills": [],
            "projects": [],
            "experience": [],
            "education": [],
        }


# ── Step 3: Save to Database ──────────────────────────────────────

def save_resume_to_db(
    guest_id: str,
    raw_text: str,
    parsed_data: dict,
    db: Session,
) -> Resume:
    """
    Save the resume to the SQLite database.

    WHY store raw_text?
      Enables re-parsing later if we improve the extraction prompt.
      Also needed for chunking and embedding (Step 4).

    WHY store parsed_data as JSON string?
      SQLite doesn't have a native JSON column type.
      We serialize the dict to a JSON string and deserialize when reading.
      json.dumps() → stored as TEXT in DB
      json.loads() → parsed back to dict when reading
    """
    # Check if user already has a resume — update it if so
    existing = db.exec(
        select(Resume).where(Resume.guest_id == guest_id)
    ).first()

    if existing:
        # Update existing resume (user re-uploaded)
        existing.raw_text = raw_text
        existing.parsed_data = json.dumps(parsed_data)
        existing.chunks_embedded = False  # Will be re-embedded
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new resume record
        resume = Resume(
            guest_id=guest_id,
            raw_text=raw_text,
            parsed_data=json.dumps(parsed_data),
            chunks_embedded=False,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        return resume


def mark_resume_embedded(resume_id: int, db: Session):
    """Mark a resume's chunks as embedded in ChromaDB."""
    resume = db.get(Resume, resume_id)
    if resume:
        resume.chunks_embedded = True
        db.add(resume)
        db.commit()


# ── Step 4: Embed Resume Chunks for RAG ───────────────────────────

def embed_resume_for_rag(guest_id: str, raw_text: str) -> int:
    """
    Chunk the resume text and store embeddings in ChromaDB.

    WHY CHUNK THE RESUME?
      The entire resume might be 2000+ characters — too long for a single vector.
      A vector of the whole resume is too abstract: it tries to represent EVERYTHING.
      
      Solution: Split into smaller chunks. Each chunk has a focused meaning:
        Chunk 1: "Skills: Python, React, MongoDB, Docker..."
        Chunk 2: "Project: Blockchain Supply Chain using Hyperledger Fabric..."
        Chunk 3: "Work Experience: Backend Developer at XYZ Corp..."
      
      When the AI asks "tell me about your Python projects",
      the retriever finds Chunk 1 (skills) + Chunk 2 (blockchain project)
      because their MEANING is similar to the query.

    CHUNK SIZE:
      400 chars, 50 overlap — smaller than knowledge base chunks (800)
      because resume sections are naturally short and discrete.

    METADATA TAGGED ON EACH CHUNK:
      guest_id: "abc-123"         → filter to THIS user's resume only
      source: "resume"            → identifies this as a resume chunk (not KB)
      interview_type: "resume"    → so resume-type retriever finds it

    Returns:
        Number of chunks stored in ChromaDB
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=["\n\n", "\n", " ", ""],
    )

    # create_documents wraps text strings into Document objects
    chunks = splitter.create_documents([raw_text])

    # Tag each chunk with metadata for filtered retrieval
    for chunk in chunks:
        chunk.metadata["guest_id"] = guest_id
        chunk.metadata["source"] = "resume"
        chunk.metadata["interview_type"] = "resume"

    if not chunks:
        return 0

    # Add to ChromaDB "resumes" collection
    # This calls the embedding model (Google text-embedding-004) for each chunk
    store = get_resume_store()
    store.add_documents(chunks)

    print(f"✅ Embedded {len(chunks)} resume chunks for guest_id={guest_id}")
    return len(chunks)
