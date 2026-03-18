# SPEC 13 - RAG Knowledge Ingestion and Content Plan

Status: Active  
Date: 2026-03-16

---

## 1. Objective

Enable PrepLingo to ingest multi-format knowledge documents for RAG so question generation remains grounded across interview types.

---

## 2. Supported Source Formats

The ingestion pipeline now supports:
1. `.md`
2. `.txt`
3. `.pdf`
4. `.docx`
5. `.html` / `.htm`

Primary script:
- `backend/scripts/ingest_knowledge.py`

Knowledge roots:
1. `backend/knowledge_base/` (curated docs)
2. `backend/knowledge_raw/` (external articles and references)

---

## 3. Metadata Strategy

Each source document is normalized with metadata:
1. `source`
2. `source_type`
3. `interview_type`
4. `topic`
5. `title`
6. `content_hash`

Chunks additionally include:
1. `chunk_index`
2. `chunk_hash`

This metadata supports filtering and auditability during retrieval.

---

## 4. Ingestion Behavior

1. Scan all supported files in both roots.
2. Parse and normalize text based on file type.
3. Chunk using recursive splitter.
4. Replace chunks by `source` in Chroma to avoid duplicates on reruns.
5. Embed and store in `knowledge` collection.
6. Run a retrieval smoke test.

Reset mode:
- `python scripts/ingest_knowledge.py --reset`
- Deletes and rebuilds only the `knowledge` collection.

Automated source collection:
- `python scripts/collect_knowledge_sources.py`
- Reads seeds from `backend/knowledge_raw/seed_sources.json`
- Discovers topic-relevant links and downloads HTML/PDF files into topic folders.
- Writes discovery report to `backend/knowledge_raw/discovery_report.md`.

---

## 5. Content Taxonomy

Use this folder taxonomy in `knowledge_raw/`:

```text
knowledge_raw/
  technical/
  system_design/
  behavioral/
  resume_interview/
```

This ensures interview_type tagging is deterministic.

---

## 6. Content Quality Rules

1. Prefer concise, concept-dense sources.
2. Avoid duplicate versions of near-identical articles.
3. Exclude low-signal marketing content.
4. Keep files named clearly by topic.
5. Favor evergreen engineering references over trend-only posts.

---

## 7. Recommended Seed Topics

Technical:
1. Database indexing and query planning
2. Transactions and isolation levels
3. REST API design and pagination
4. Caching patterns and invalidation
5. Async processing and message queues

System Design:
1. URL shortener
2. Rate limiter
3. Notification system
4. Feed/timeline architecture
5. Distributed caching and consistency

Behavioral:
1. STAR method examples
2. Conflict resolution stories
3. Ownership and prioritization examples
4. Ambiguity handling frameworks
5. Leadership and collaboration patterns

Resume Interview:
1. Project deep-dive question banks
2. Metrics-oriented follow-up prompts
3. Trade-off discussion templates
4. Architecture justification prompts

---

## 8. Verification Checklist

After adding documents:
1. (Optional) Run source collection script to gather new docs from seed URLs.
1. Run ingestion script.
2. Confirm non-zero chunk creation per target interview type.
3. Run `test_phase5_pdf_relevance.py` and `test_phase5_edge_cases.py`.
4. Validate generated interview questions include domain grounding.

---

## 9. Definition of Done

RAG knowledge ingestion is considered healthy when:
1. Multi-format files ingest without parser failures.
2. Retrieval smoke test returns relevant chunks.
3. Interview flows remain stable.
4. Added knowledge improves topical question relevance.
