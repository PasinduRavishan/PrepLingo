# System Design Case Study — URL Shortener (e.g., bit.ly, TinyURL)

## Problem Statement

Design a URL shortening service where:
- Users submit a long URL → get a short URL (e.g., short.ly/abc123)
- Anyone with the short URL is redirected to the original long URL
- System must handle millions of daily active users

---

## Step 1: Requirements Clarification (Always Start Here)

**Functional Requirements:**
- Shorten a long URL to a unique short URL
- Redirect short URL → original URL (fast, must be <100ms)
- Short URLs should be ~6-8 characters
- Custom aliases (optional): user can choose "short.ly/mylink"
- Analytics: click counts, geographic data (optional)

**Non-Functional Requirements:**
- High availability (99.99% uptime) — if service is down, links are dead
- Low latency for redirects (reads >> writes — 100:1 ratio)
- Durability — short URLs shouldn't expire unless explicitly set
- Scale: 100M URLs per day, 10B total URLs

**Estimations (back-of-envelope):**
- Write: 100M URLs / 86400 sec = ~1,200 writes/sec
- Read: 10B requests / 86400 sec = ~115,000 reads/sec
- Storage: 500 bytes/URL × 10B = 5TB
- Cache: 20% of traffic hits 80% of URLs (Pareto) → cache 20% = 20GB/day

---

## Step 2: High-Level Design

```
Client → Load Balancer → [Short URL Service] → Cache (Redis)
                                             → Database (URL Mapping)
```

**Components:**
1. **URL Shortener Service** — generates short codes, stores mappings
2. **Redirect Service** — resolves short codes → original URL (read path)
3. **Cache (Redis)** — stores hot short codes (LRU, TTL=1 day)
4. **Database** — stores all URL mappings (write once, read many)

**Read path (redirect):**
```
GET /abc123
→ Check Redis cache → HIT: 301 Redirect
→ Cache MISS → Query DB → Store in cache → 301 Redirect
```

---

## Step 3: URL Shortening Algorithm

**Approach 1: MD5/SHA hash of long URL**
- Hash(long_url) → take first 6 chars as short code
- Problem: collisions (two URLs map to same short code)
- Problem: same long URL → same short code (intentional? depends on requirements)

**Approach 2: Base62 encoding of auto-increment ID**
- Database auto-increments ID: 1, 2, 3, ...
- Convert to base62: digits + uppercase + lowercase (0-9, A-Z, a-z)
- ID 125 → "cb" → short.ly/cb
- No collisions guaranteed (each ID is unique)
- 6 chars: 62^6 = 56 billion unique URLs

**Approach 3: Pre-generate random short codes**
- Generate batch of unique codes offline → store in a "keys" table
- When URL submitted → take an unused key → assign to URL
- Always available, no collision resolution needed at write time

**Best answer:** Base62 or pre-generated keys. MD5 approach has collision issues.

---

## Step 4: Database Design

```sql
urls (table)
  id          BIGINT PRIMARY KEY AUTO_INCREMENT
  short_code  VARCHAR(8) UNIQUE INDEX
  long_url    VARCHAR(2048) NOT NULL
  user_id     BIGINT (nullable — for registered users)
  created_at  TIMESTAMP
  expires_at  TIMESTAMP (nullable)
  click_count BIGINT DEFAULT 0
```

**Storage choice: SQL vs NoSQL?**
- SQL (PostgreSQL): Easy to start, ACID for write-once data, good for joins
- NoSQL (DynamoDB): Key-value reads (short_code → long_url) fit perfectly
- For 10B rows: NoSQL (Cassandra/DynamoDB) scales better
- For MVP: PostgreSQL is fine

---

## Step 5: Scaling the System

**Horizontal Scaling of Application Tier:**
- Add more URL service instances behind a load balancer
- Sessions are stateless — easy to scale

**Cache Layer (Redis):**
- Read ratio is 100:1 (reads >>> writes)
- Cache 20% of URLs (most popular) — serves 80% of traffic
- Redis cluster for cache size > single node

**Database Scaling:**
- Read replicas — direct all reads to replicas, writes to primary
- Sharding on short_code: hash(short_code) % N shards
- Problem: auto-increment IDs don't work with sharding
- Solution: Use pre-generated unique IDs (Snowflake-style) or UUID

**Redirect optimization:**
- Use 301 Permanent Redirect for static URLs (browser caches it — no repeat requests to us)
- Use 302 Temporary Redirect if you want to count every click

---

## Step 6: Handling Edge Cases

**Custom aliases:**
- Check for conflicts with reserved words and existing codes
- Shorter TTL or no TTL → user manages

**Analytics:**
- Async counter updates (don't block redirect for count increment)
- Use a message queue: redirect happens → event published → analytics consumer updates count

**Abuse prevention:**
- Rate limiting per IP/user for URL creation
- URL scanning for malware/spam before shortening

---

## Common Interview Follow-Up Questions

- Q: How would you handle 10x traffic spike suddenly?
- Q: What's your database replication strategy?
- Q: How do you ensure no two servers generate the same short code?
- Q: How would you add analytics (clicks per country, per device)?
- Q: What happens if your primary database goes down?
