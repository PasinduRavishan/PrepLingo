# Automated Knowledge Collector

Use this script to discover and download documentation pages for RAG.

Script:
- `backend/scripts/collect_knowledge_sources.py`

Seed config:
- `backend/knowledge_raw/seed_sources.json`

## Run

```bash
cd backend
python scripts/collect_knowledge_sources.py
```

Discover only (no downloads):

```bash
cd backend
python scripts/collect_knowledge_sources.py --discover-only
```

Tune limits:

```bash
cd backend
python scripts/collect_knowledge_sources.py --max-links-per-seed 8 --max-downloads-per-topic 12
```

Target only selected topics:

```bash
cd backend
python scripts/collect_knowledge_sources.py --discover-only --targets technical/databases,system_design/scalability_patterns
```

Adjust timeout for slow sites:

```bash
cd backend
python scripts/collect_knowledge_sources.py --timeout-seconds 8
```

After collection:

```bash
cd backend
python scripts/ingest_knowledge.py
```

## Notes

1. The collector intentionally stays conservative and prefers same-domain links from each seed.
2. Review downloaded content quality before ingestion for best RAG results.
3. Respect source website terms and robots policies when adding new domains.
