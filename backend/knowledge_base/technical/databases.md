# Database Concepts — Technical Interview Knowledge Base

## What is Database Indexing?

Database indexing is a technique to speed up data retrieval operations on a database table.
An index creates a separate data structure (usually a B-tree or Hash table) that maps
column values to the rows containing them, allowing the database to find rows without
scanning the entire table.

**Without an index:** Full table scan — O(n) — slow for large tables.
**With an index:** Lookup via B-tree — O(log n) — fast even for millions of rows.

### Types of Indexes

**Clustered Index:**
- The table data is physically sorted by this column
- Only ONE clustered index allowed per table (it IS the table's physical order)
- In SQL Server/MySQL: Primary Key is often the clustered index by default
- Fast for range queries: `WHERE age BETWEEN 25 AND 35`

**Non-Clustered Index:**
- A separate structure that stores (indexed_value → row pointer)
- Multiple allowed per table
- Fast for exact lookups: `WHERE email = 'x@y.com'`
- Extra memory cost; slows down INSERT/UPDATE (index must be updated too)

**Composite Index:**
- Index on multiple columns: `(last_name, first_name)`
- Follow the "leftmost prefix rule" — the index is only used if the query 
  filters on the leftmost columns in the index definition
- Example: index on (A, B, C) helps queries filtering on A, or A+B, but NOT on B alone

**Partial Index:**
- Index only a subset of rows: `WHERE status = 'active'`
- Smaller index size, faster for queries targeting that subset

### When NOT to Add an Index
- Small tables (full scan is often faster than index lookup)
- Columns with low cardinality (few unique values, like boolean or gender)
- Columns that are rarely queried
- Tables with very high write rate (index maintenance overhead)

### Common Interview Questions About Indexing
- Q: What is the difference between clustered and non-clustered?
- Q: Explain the B-tree structure of an index
- Q: When would you choose a Hash index over a B-tree index?
- Q: What is covering index / index-only scan?
- Q: How do you identify which columns need indexes in a slow query?

---

## ACID Properties

ACID ensures database transactions are processed reliably.

**Atomicity** — "All or nothing"
- A transaction either completes fully or has no effect at all
- Example: Bank transfer deducts from A AND credits to B, or does neither
- Mechanism: Transaction log — if failure, roll back all changes

**Consistency** — "Data stays valid"
- A transaction brings the database from one valid state to another
- All constraints, rules, cascades are enforced
- Example: Can't transfer more money than account balance (CHECK constraint)

**Isolation** — "Transactions don't interfere"
- Concurrent transactions behave as if they run sequentially
- Isolation levels: READ UNCOMMITTED → READ COMMITTED → REPEATABLE READ → SERIALIZABLE
- Higher isolation = fewer anomalies but lower throughput

**Durability** — "Committed data survives crashes"
- Once committed, data persists even if the system crashes immediately after
- Mechanism: Write-Ahead Log (WAL) — changes written to disk before confirming commit

---

## SQL vs NoSQL

### When to Use SQL (Relational)
- Structured data with clear relationships
- Need for complex JOINs and aggregations
- Financial/transactional data requiring ACID
- Data that changes structure rarely
- Examples: MySQL, PostgreSQL

### When to Use NoSQL
- Flexible/evolving schema (document stores)
- Massive horizontal scalability (sharding)
- High write throughput (Cassandra)
- Graph relationships (Neo4j)
- Key-value caching (Redis)

### Types of NoSQL
- **Document:** MongoDB, CouchDB — JSON-like documents
- **Key-Value:** Redis, DynamoDB — simple get/set
- **Column-Family:** Cassandra — wide rows, optimized for writes
- **Graph:** Neo4j — entities and relationships

### CAP Theorem
A distributed system can guarantee only 2 of 3 properties:
- **Consistency** — all nodes see the same data at the same time
- **Availability** — every request gets a response (maybe stale)
- **Partition Tolerance** — system works despite network failures

Network partitions WILL happen. So real choice is CP vs AP:
- CP (Consistent + Partition-tolerant): MongoDB, HBase — returns error if can't guarantee consistent read
- AP (Available + Partition-tolerant): CouchDB, Cassandra — returns best available data (may be stale)

---

## Database Normalization

Normalization reduces data redundancy and improves integrity.

**1NF:** Each column holds atomic values, no repeating groups
**2NF:** 1NF + no partial dependency (non-key columns depend on FULL key)
**3NF:** 2NF + no transitive dependency (non-key columns don't depend on other non-key columns)
**BCNF:** Stricter 3NF — every determinant is a candidate key

**Denormalization:** Intentionally adding redundancy for performance
- Read-heavy systems often denormalize to avoid expensive JOINs
- Trade: faster reads, but more complex writes and potential inconsistency
