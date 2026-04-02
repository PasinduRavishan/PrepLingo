# knowledge_raw

Drop additional source material here for RAG ingestion.

Supported file types:
- `.md`
- `.txt`
- `.pdf`
- `.docx`
- `.html` / `.htm`

Suggested folder pattern:

```text
knowledge_raw/
  technical/
  system_design/
  behavioral/
  resume_interview/
```

Any file path containing one of the interview-type folders above is tagged automatically.

Example:
- `knowledge_raw/system_design/case_studies/discord_architecture.pdf`
- `knowledge_raw/technical/databases/postgres_indexing.html`

Run ingestion after adding files:

```bash
cd backend
python scripts/ingest_knowledge.py
```

To fully rebuild the knowledge collection:

```bash
cd backend
python scripts/ingest_knowledge.py --reset
```
