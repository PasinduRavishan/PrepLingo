# SPEC 04 — Data Models

**Status:** ✅ IMPLEMENTED (Phase 0/1)
**Files Created:** `backend/app/models/`

---

## Overview

All database models use **SQLModel** — which combines Pydantic (data validation)
with SQLAlchemy (database ORM) into one class per table.

Classes with `table=True` create actual database tables.
Pydantic models without `table=True` are used for API request/response schemas.

---

## Entity Relationship Diagram

```
GuestUser (1) ──────── (many) Resume
                               │
                               │ (optional)
GuestUser (1) ──────── (many) InterviewSession
                               │
                     ┌─────────┴─────────┐
                     │                   │
              (many) Message      (many) Evaluation
                                         │
                                  (one)  Report
```

---

## Table: `guest_users`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR UNIQUE | UUID from browser localStorage |
| `name` | VARCHAR | Optional, null in guest mode |
| `created_at` | DATETIME | Auto-set |

**Why guest_id?** Allows guest mode (no email/password required).
The browser generates a UUID, stores it in localStorage, and sends it with every request.

---

## Table: `resumes`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR INDEX | Links to guest_users.guest_id |
| `raw_text` | TEXT | Full extracted text from PDF |
| `parsed_data` | TEXT | JSON string — structured extraction by Gemini |
| `chunks_embedded` | BOOLEAN | Whether resume is in ChromaDB |
| `created_at` | DATETIME | Upload time |

**parsed_data JSON schema:**
```json
{
  "name": "string",
  "skills": ["Python", "React"],
  "projects": [{"name": "...", "description": "...", "tech_stack": [...], "outcomes": "..."}],
  "experience": [{"role": "...", "company": "...", "duration": "..."}],
  "education": [{"degree": "...", "institution": "...", "year": "..."}]
}
```

---

## Table: `interview_sessions`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `guest_id` | VARCHAR INDEX | Session owner |
| `interview_type` | ENUM | resume / technical / system_design / behavioral |
| `status` | ENUM | in_progress / completed |
| `question_count` | INTEGER | Current question number (0-8) |
| `max_questions` | INTEGER | Default 8 |
| `resume_id` | INTEGER FK | Optional link to uploaded resume |
| `created_at` | DATETIME | Session start time |
| `ended_at` | DATETIME | Session end time (null if in_progress) |

---

## Table: `messages`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK | Which session |
| `role` | ENUM | ai / user |
| `content` | TEXT | The question or answer text |
| `question_number` | INTEGER | Null for user messages, 1-8 for AI |
| `ai_question_asked` | TEXT | For user messages: what was the AI question |
| `created_at` | DATETIME | Timestamp |

**Why store `ai_question_asked` on user messages?**
EvaluationChain needs both the question AND the answer together.
Storing it denormalized avoids a JOIN at evaluation time.

---

## Table: `evaluations`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK INDEX | Which session |
| `message_id` | INTEGER FK | Which user answer was evaluated |
| `question_number` | INTEGER | 1-8, correlates to AI messages |
| `technical_correctness` | INTEGER | 0-10 |
| `depth_of_explanation` | INTEGER | 0-10 |
| `clarity` | INTEGER | 0-10 |
| `overall_score` | INTEGER | 0-10 (weighted average) |
| `strengths` | TEXT | JSON array of strength strings |
| `weaknesses` | TEXT | JSON array of weakness strings |
| `suggestions` | TEXT | JSON array of suggestion strings |
| `created_at` | DATETIME | When evaluated |

---

## Table: `reports`

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `session_id` | INTEGER FK UNIQUE | One report per session |
| `interview_type` | VARCHAR | Duplicated for display without JOIN |
| `overall_score` | FLOAT | 0-100 percentage |
| `per_question_scores` | TEXT | JSON array: [8, 6, 7, 5, 8, 7, 6, 8] |
| `per_dimension_scores` | TEXT | JSON: {technical: 7.2, clarity: 8.1} |
| `top_strengths` | TEXT | JSON array of top 3 |
| `top_weaknesses` | TEXT | JSON array of top 3 |
| `suggestions` | TEXT | JSON array of actionable suggestions |
| `created_at` | DATETIME | Report generation time |

---

## Implementation Notes

- **JSON as TEXT in SQLite:** SQLite doesn't have a native JSON column type.
  We store JSON-serialized strings and parse them in Python with `json.loads()`.
  In PostgreSQL, we'd use the `JSON` or `JSONB` column type.

- **No foreign key cascade rules in SQLite by default:**
  SQLite supports foreign keys but they're not enforced by default.
  FastAPI + SQLModel handles relationship integrity at the application level.

- **models/__init__.py imports all models:**
  This is required so SQLModel.metadata knows about all tables
  before `create_all()` is called at startup.
