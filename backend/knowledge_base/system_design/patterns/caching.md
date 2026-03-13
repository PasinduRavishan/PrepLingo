# System Design — Caching Strategies

## What is Caching?

Caching stores frequently accessed data in a fast-access layer (memory) to reduce
load on slower data sources (databases, external APIs). Cache reads are 10-100x
faster than database reads.

**Without cache:** Every request hits the database
**With cache:** Most requests served from memory — database only for cache misses

---

## Cache-Aside (Lazy Loading)

The most common caching pattern. Application manages the cache manually.

**Read flow:**
1. Check cache — if hit, return data
2. If miss → query database → store in cache → return data

**Write flow:**
1. Write to database
2. Invalidate (delete) the cache entry — force fresh load on next read

**Pros:** Only caches what's actually requested, cache failure doesn't break reads
**Cons:** First request after miss is slow (cache miss), stale data possible

**When to use:** Read-heavy workloads where you can tolerate brief staleness
**Used by:** Most general-purpose caching (product catalog, user profiles)

```
App → Redis GET user:123    → MISS
App → PostgreSQL SELECT ...  → row found
App → Redis SET user:123 {..} TTL 5min
App → return data
```

---

## Write-Through Cache

Application writes to cache AND database simultaneously.

**Write flow:**
1. Write to cache
2. Write to database (synchronously)
3. Return success

**Pros:** Cache is always up-to-date, no stale reads
**Cons:** Every write is slower (two writes), cache may fill with rarely-read data

**When to use:** Consistency is critical; acceptable write latency increase
**Used by:** Banking transactions, session data

---

## Write-Behind (Write-Back)

Application writes to cache only. Database is updated asynchronously.

**Write flow:**
1. Write to cache → return success IMMEDIATELY
2. Background job periodically flushes cache to database

**Pros:** Very fast writes (single in-memory write)
**Cons:** Risk of data loss if cache crashes before flush; complex consistency

**When to use:** High write throughput, can tolerate brief inconsistency
**Used by:** Analytics counters, gaming leaderboards

---

## Cache Eviction Policies

When cache is full, old entries must be removed:

**LRU (Least Recently Used):** Evict the entry that hasn't been accessed the longest
- Best general default — keeps "hot" data in cache
- Used by: Redis (with `maxmemory-policy allkeys-lru`)

**LFU (Least Frequently Used):** Evict the entry accessed the fewest times
- Better for non-uniform access patterns — protects frequently accessed items
- More memory overhead to track frequency

**TTL (Time-To-Live):** Every entry expires after a set time
- Simple, effective — automatically clears stale data
- Always combine TTL with LRU for best results

**FIFO (First In, First Out):** Evict the oldest entry regardless of access
- Simple to implement but ignores access patterns — rarely optimal

---

## Cache Invalidation — The Hard Problem

> "There are only two hard things in Computer Science: cache invalidation and naming things." — Phil Karlton

**Strategies:**

**TTL (Expiry-based):** Entry expires after N seconds
- Pro: simple; Con: stale window = TTL duration

**Event-based invalidation:** When data changes, explicitly delete cache key
- Pro: immediately consistent; Con: requires coordination between services

**Versioning:** Cache key includes version number: `user:123:v2`
- Pro: no invalidation needed — old keys just expire; Con: key explosion

---

## Redis vs Memcached

| Feature | Redis | Memcached |
|---------|-------|-----------|
| Data types | String, Hash, List, Set, ZSet | String only |
| Persistence | Yes (RDB/AOF) | No |
| Pub/Sub | Yes | No |
| Clustering | Yes (Redis Cluster) | Yes (client-side) |
| Use case | Caching + more | Pure caching |

**Recommendation:** Default to Redis — more features, still very fast.

---

## Common Interview Questions About Caching

- Q: What cache pattern would you use for a user profile service?
- Q: How do you handle cache stampede / thundering herd?
- Q: What's the difference between Redis and Memcached?
- Q: How would you cache database query results?
- Q: Explain cache warming and why it matters
- Q: How do you size your cache? What % of your dataset should be cached?
