# SPEC 00 — Project Overview

**Project:** PrepLingo — AI Interview Trainer  
**Version:** 0.1 (Draft)  
**Status:** In Design

---

## Vision

PrepLingo is a web-based AI interview simulator that conducts realistic mock interviews
using the user's own resume as a primary knowledge source, combined with curated
domain-specific knowledge bases. Every interview type is powered by RAG — meaning
the AI retrieves and grounds its questions and evaluations in real knowledge, not hallucinations.

---

## What We Are Building

A user logs in → uploads their CV → selects an interview type → enters a live
chat-based interview session where the AI:
1. Reads their CV context
2. Retrieves relevant knowledge from the RAG knowledge base
3. Asks tailored, grounded questions
4. Evaluates responses against a rubric
5. Generates a final report with scores and suggestions

---

## Four Interview Types (All RAG-Powered)

| Type | Primary Knowledge Source | CV Role |
|---|---|---|
| Resume-Based | User's CV (primary) | The knowledge base itself |
| Technical | CS/Engineering concepts DB | Filters topics by CV skills |
| System Design | Architecture & design patterns DB | Anchors problems to CV projects |
| Behavioral | STAR framework & behavioral guides | Pulls project stories from CV |

---

## What We Are NOT Building (Non-Goals)

- No voice interviews (future enhancement)
- No real company interview simulation (future)
- No diagram analysis (future)
- No production deployment (learning project scope)
- No payment system

---

## Glossary

| Term | Meaning |
|---|---|
| RAG | Retrieval-Augmented Generation — fetch relevant context, then generate |
| Knowledge Base | Curated documents embedded and stored in a vector database |
| Session | A single interview run between user and AI |
| Evaluation | AI-generated scoring of a user's response |
| Report | Final compiled summary of an entire interview session |
| Chunk | A piece of a document split for embedding |
| Embedding | A vector representation of text for semantic search |
| CV / Resume | User's uploaded PDF resume |

---

## Technology Choices (To Be Confirmed via Decisions Doc)

- **Backend:** FastAPI (Python)
- **AI Orchestration:** LangChain (LCEL)
- **LLM Provider:** TBD (OpenAI / Gemini / Ollama)
- **Vector Store:** TBD (FAISS / ChromaDB)
- **Embeddings:** TBD (OpenAI / HuggingFace)
- **Database:** SQLite → PostgreSQL
- **Frontend:** Next.js (React)
- **Auth:** JWT

---

## Learning Outcomes

By building PrepLingo, you will learn:
- LangChain LCEL chain composition
- RAG pipeline design and implementation
- Vector database management (ingestion, retrieval, re-ranking)
- Prompt engineering for multi-turn conversations
- FastAPI service design
- Structured LLM output parsing (Pydantic)
- Full-stack integration (Next.js + FastAPI)
