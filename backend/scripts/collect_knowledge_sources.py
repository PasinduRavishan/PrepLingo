"""Discover and download external knowledge docs for RAG.

This script reads seed URLs from knowledge_raw/seed_sources.json,
finds relevant links from those pages, and downloads HTML/PDF content into:

  knowledge_raw/<interview_type>/<topic>/

Usage:
  cd backend
  python scripts/collect_knowledge_sources.py
  python scripts/collect_knowledge_sources.py --discover-only
  python scripts/collect_knowledge_sources.py --max-links-per-seed 8 --max-downloads-per-topic 12
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
KNOWLEDGE_RAW_DIR = BACKEND_DIR / "knowledge_raw"
SEED_CONFIG_PATH = KNOWLEDGE_RAW_DIR / "seed_sources.json"
REPORT_PATH = KNOWLEDGE_RAW_DIR / "discovery_report.md"

USER_AGENT = "PrepLingoKnowledgeCollector/1.0 (+https://localhost)"
DEFAULT_TIMEOUT_SECONDS = 12

ALLOWED_DOWNLOAD_EXTENSIONS = {".html", ".htm", ".pdf", ""}
SKIP_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".mp4", ".css", ".js"}


def fetch_url(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[bytes | None, str | None]:
    """Fetch URL and return payload bytes and content-type."""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=timeout) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            return response.read(), content_type
    except Exception as exc:
        print(f"   WARN fetch failed: {url} ({exc})")
        return None, None


def extract_links(html: str, base_url: str) -> list[str]:
    """Extract absolute links from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[str] = []
    seen = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "").strip()
        if not href:
            continue
        absolute = urljoin(base_url, href)
        absolute, _fragment = urldefrag(absolute)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if absolute not in seen:
            seen.add(absolute)
            out.append(absolute)

    return out


def sanitize_filename(name: str) -> str:
    """Return filesystem-safe name."""
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    safe = safe.strip("._")
    return safe[:120] or "doc"


def canonicalize_url(url: str) -> str:
    """Normalize URL for deduplication (strip query/fragment, trim trailing slash)."""
    clean, _fragment = urldefrag(url)
    parsed = urlparse(clean)
    normalized_path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"


def choose_extension(url: str, content_type: str | None) -> str:
    """Determine file extension from URL/content type."""
    path = urlparse(url).path.lower()
    if path.endswith(".pdf") or (content_type and "application/pdf" in content_type):
        return ".pdf"
    if path.endswith(".html") or path.endswith(".htm"):
        return Path(path).suffix
    return ".html"


def is_relevant(url: str, topic_keywords: list[str], seed_domain: str) -> bool:
    """Heuristic relevance filter for discovered links."""
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()

    # Keep discovery controlled: same domain as seed.
    if seed_domain not in host:
        return False

    for suffix in SKIP_SUFFIXES:
        if path.endswith(suffix):
            return False

    ext = Path(path).suffix.lower()
    if ext not in ALLOWED_DOWNLOAD_EXTENSIONS:
        return False

    if not topic_keywords:
        return True

    hay = f"{host}{path}".lower()
    return any(keyword in hay for keyword in topic_keywords)


def topic_keywords(interview_type: str, topic: str) -> list[str]:
    """Build keyword set used for link filtering."""
    base = [w.lower() for w in topic.replace("_", " ").split() if w.strip()]
    extras = {
        "technical": ["api", "database", "index", "cache", "queue", "async", "http", "redis"],
        "system_design": ["scale", "distributed", "architecture", "consistency", "availability", "latency"],
        "behavioral": ["interview", "leadership", "conflict", "communication", "star", "team"],
        "resume_interview": ["project", "metrics", "impact", "tradeoff", "interview"],
    }
    return sorted(set(base + extras.get(interview_type, [])))


def load_seed_config(path: Path) -> dict:
    """Load JSON configuration for source discovery."""
    if not path.exists():
        raise FileNotFoundError(f"Seed config not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_download(content: bytes, destination: Path):
    """Write payload to disk."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def collect_for_topic(
    interview_type: str,
    topic: str,
    seeds: list[str],
    max_links_per_seed: int,
    max_downloads_per_topic: int,
    discover_only: bool,
    timeout_seconds: int,
) -> dict:
    """Discover and optionally download topic-relevant resources."""
    keywords = topic_keywords(interview_type, topic)
    topic_dir = KNOWLEDGE_RAW_DIR / interview_type / topic
    topic_dir.mkdir(parents=True, exist_ok=True)

    discovered: list[str] = []
    downloaded: list[str] = []
    discovered_keys: set[str] = set()
    downloaded_keys: set[str] = set()

    for seed in seeds:
        print(f" - Seed: {seed}")
        seed_domain = (urlparse(seed).netloc or "").lower()

        canonical_seed = canonicalize_url(seed)
        seed_payload, seed_content_type = fetch_url(seed, timeout=timeout_seconds)
        if not seed_payload:
            continue

        seed_ext = choose_extension(seed, seed_content_type)
        seed_slug = sanitize_filename(Path(urlparse(seed).path).stem or "index")
        seed_hash = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
        seed_name = f"seed_{seed_slug}_{seed_hash}{seed_ext}"
        if not discover_only and canonical_seed not in downloaded_keys:
            save_download(seed_payload, topic_dir / seed_name)
            downloaded.append(seed)
            downloaded_keys.add(canonical_seed)

        if "html" not in (seed_content_type or "") and not seed.endswith((".html", ".htm", "/")):
            continue

        try:
            html = seed_payload.decode("utf-8", errors="ignore")
            links = extract_links(html, seed)
        except Exception:
            continue

        candidates = []
        for link in links:
            if is_relevant(link, keywords, seed_domain):
                candidates.append(link)
            if len(candidates) >= max_links_per_seed:
                break

        for link in candidates:
            canonical_link = canonicalize_url(link)
            if canonical_link not in discovered_keys:
                discovered.append(link)
                discovered_keys.add(canonical_link)

            if discover_only or len(downloaded) >= max_downloads_per_topic:
                continue

            if canonical_link in downloaded_keys:
                continue

            payload, content_type = fetch_url(link, timeout=timeout_seconds)
            if not payload:
                continue

            ext = choose_extension(link, content_type)
            slug = sanitize_filename(Path(urlparse(link).path).stem or "page")
            short = hashlib.sha1(link.encode("utf-8")).hexdigest()[:8]
            file_name = f"{slug}_{short}{ext}"
            save_download(payload, topic_dir / file_name)
            downloaded.append(link)
            downloaded_keys.add(canonical_link)

            if len(downloaded) >= max_downloads_per_topic:
                break

    return {
        "interview_type": interview_type,
        "topic": topic,
        "seeds": seeds,
        "discovered": discovered,
        "downloaded": downloaded,
    }


def write_report(results: list[dict], discover_only: bool):
    """Write markdown report of discovery/download execution."""
    lines = [
        "# Knowledge Source Discovery Report",
        "",
        f"Mode: {'discover-only' if discover_only else 'discover-and-download'}",
        "",
    ]

    for item in results:
        lines.append(f"## {item['interview_type']} / {item['topic']}")
        lines.append("")
        lines.append(f"Seeds: {len(item['seeds'])}")
        lines.append(f"Discovered links: {len(item['discovered'])}")
        lines.append(f"Downloaded links: {len(item['downloaded'])}")
        lines.append("")

        if item["downloaded"]:
            lines.append("Downloaded URLs:")
            for url in item["downloaded"]:
                lines.append(f"- {url}")
            lines.append("")

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Discover and download RAG knowledge sources")
    parser.add_argument("--discover-only", action="store_true", help="Only discover links, do not download")
    parser.add_argument("--max-links-per-seed", type=int, default=6, help="Max discovered links from each seed page")
    parser.add_argument("--max-downloads-per-topic", type=int, default=10, help="Max downloaded pages/PDFs per topic")
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP request timeout per URL",
    )
    parser.add_argument(
        "--targets",
        type=str,
        default="",
        help="Comma-separated targets as interview_type/topic, e.g. technical/databases,system_design/scalability_patterns",
    )
    args = parser.parse_args()

    config = load_seed_config(SEED_CONFIG_PATH)
    results: list[dict] = []

    selected_targets: set[str] = set()
    if args.targets.strip():
        selected_targets = {item.strip().lower() for item in args.targets.split(",") if item.strip()}

    print("=" * 64)
    print("PrepLingo Knowledge Source Collector")
    print("=" * 64)

    for interview_type, topic_map in config.items():
        print(f"\nCollecting for interview_type={interview_type}")
        for topic, seeds in topic_map.items():
            target_key = f"{interview_type}/{topic}".lower()
            if selected_targets and target_key not in selected_targets:
                continue
            print(f"\nTopic={topic}")
            result = collect_for_topic(
                interview_type=interview_type,
                topic=topic,
                seeds=seeds,
                max_links_per_seed=args.max_links_per_seed,
                max_downloads_per_topic=args.max_downloads_per_topic,
                discover_only=args.discover_only,
                timeout_seconds=args.timeout_seconds,
            )
            results.append(result)

    write_report(results, discover_only=args.discover_only)

    print("\n" + "=" * 64)
    print("Collection complete")
    print(f"Report: {REPORT_PATH}")
    if not args.discover_only:
        print("Next: python scripts/ingest_knowledge.py")
    print("=" * 64)


if __name__ == "__main__":
    main()
