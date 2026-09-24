# System design

## What framework do you use to answer a system design question?
Tags: approach

1. Clarify functional and non-functional requirements (scale, latency, consistency).
2. Estimate: users, QPS, storage, bandwidth.
3. Define the API and data model.
4. Draw the high-level design.
5. Deep-dive into bottlenecks: caching, sharding, queues, failure modes.
6. Discuss trade-offs and what you'd monitor.

## Design a URL shortener.
Tags: classic

API: `POST /shorten`, `GET /{code}` → 301/302. Generate codes with base62 of an ID from a sequence/Snowflake (no collisions) or hashing with collision checks. Store code → URL in a key-value store; cache hot codes in Redis; reads dominate so scale reads with replicas + CDN. Analytics via async events to a queue.

## Design a scalable LLM-powered chat API.
Tags: genai, classic

Stateless API servers behind a load balancer; streaming responses (SSE/websockets); conversation history in Postgres, recent context in Redis; RAG service with a vector DB; request queue + per-user rate limits and token budgets; provider abstraction with retries, timeouts and fallback models; response caching; observability of latency, tokens, cost and eval scores.

## Design a job-alert system like HireTrack's ingestion.
Tags: classic

Scheduled fetchers per source → raw events on a queue → normaliser (clean HTML, extract skills) → dedupe by fingerprint (unique index) → store → matching workers score against user profiles → notification service batches digests (email/push) respecting user preferences. Idempotent consumers and a dead-letter queue for bad records.

## SQL vs NoSQL — how do you choose?
Tags: databases

SQL for relational data, transactions, and flexible queries (the default). NoSQL when you need a specific access pattern at massive scale: key-value (Redis/DynamoDB) for simple lookups, document (MongoDB) for flexible nested records, wide-column (Cassandra) for heavy writes, graph for relationship queries.

## Explain horizontal vs vertical scaling, sharding and replication.
Tags: scaling

Vertical: bigger machine (simple, limited). Horizontal: more machines (needs stateless services). Replication copies data for read scaling and availability; sharding splits data by key for write scaling — choose a key that avoids hot spots and cross-shard queries.

## What is the CAP theorem in practice?
Tags: distributed systems

During a network partition you choose consistency (reject some requests) or availability (serve possibly stale data). Most systems pick per feature: payments need consistency; a feed can be eventually consistent.

## When do you introduce a message queue?
Tags: queues

To decouple producers from consumers, absorb traffic spikes, retry failed work, and fan out events. Kafka for high-throughput ordered event logs and replay; RabbitMQ/SQS for task queues. Design consumers to be idempotent because delivery is usually at-least-once.

## How do you design for rate limiting?
Tags: reliability

Token bucket or sliding-window counters keyed by user/API key in Redis, enforced at the gateway. Return 429 with `Retry-After`. Different limits per plan and per endpoint cost (LLM endpoints by tokens, not just requests).

## Caching strategies and pitfalls?
Tags: caching

Cache-aside, write-through, write-behind; CDN for static assets. Pitfalls: stale data (TTL + explicit invalidation), cache stampede (locks or request coalescing), and caching errors. Measure hit rate.
