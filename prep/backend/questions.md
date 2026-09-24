# Backend (FastAPI, APIs, infra)

## How does dependency injection work in FastAPI?
Tags: fastapi

Declare a parameter as `Depends(fn)`; FastAPI calls `fn` per request, caches it within the request, and supports `yield` dependencies for setup/teardown (e.g. a DB session closed after the response). Dependencies can depend on others, which is how auth → current user → permissions chains are built. Override them in tests with `app.dependency_overrides`.

## When should a FastAPI endpoint be `async def` vs `def`?
Tags: fastapi, asyncio

`async def` if everything it awaits is async (httpx.AsyncClient, asyncpg). Plain `def` endpoints run in a threadpool, which is correct for blocking libraries (sync SQLAlchemy, requests). The worst case is `async def` calling blocking code — it freezes the event loop for every request.

## How would you implement authentication for an API?
Tags: auth, security

OAuth2 password/authorization-code flow issuing short-lived JWT access tokens plus refresh tokens. Hash passwords with bcrypt/argon2, validate token signature and expiry in a dependency, and check scopes/roles per route. Mention HTTPS only, token revocation (denylist or short TTL), and never storing secrets in the JWT payload.

## What makes a REST API well-designed?
Tags: api design

Resource-oriented URLs (`/applications/42`), correct verbs and status codes (201 create, 204 delete, 409 conflict, 422 validation), idempotent PUT/DELETE, pagination (cursor for large sets), filtering via query params, consistent error bodies, versioning, and an OpenAPI spec.

## How do you make a POST endpoint idempotent?
Tags: api design, reliability

Accept an `Idempotency-Key` header, store the key with the result, and return the stored result for retries. Alternatively rely on natural unique constraints (as HireTrack does with job fingerprints) and return 409 on duplicates.

## What is middleware? Give examples.
Tags: fastapi

Code that wraps every request/response: CORS, request IDs and structured logging, timing/metrics, GZip, authentication, rate limiting. In FastAPI use `@app.middleware("http")` or Starlette middleware classes.

## How would you handle a slow task (e.g. sending emails, embedding documents) in an API?
Tags: celery, queues

Don't do it in the request. Enqueue a job (Celery/RQ/Arq with Redis or RabbitMQ), return 202 with a job id, and let the client poll or receive a webhook. Use retries with exponential backoff and idempotent tasks. `BackgroundTasks` is fine only for small fire-and-forget work.

## What is caching and where would you use Redis?
Tags: redis, performance

Cache expensive reads (profile, config, LLM responses keyed by prompt hash) with a TTL; use cache-aside (read cache → miss → DB → populate). Also use Redis for rate limiting, sessions, distributed locks, and queues. Discuss invalidation and stampede protection.

## How do you test a FastAPI app?
Tags: testing

`TestClient` (or `httpx.AsyncClient` with ASGI transport) for API tests, a throwaway database per test run, dependency overrides for external services, and pure unit tests for business logic. Mock HTTP with `httpx.MockTransport` or `respx`.

## Docker: image vs container, and how do you make images small?
Tags: docker

An image is an immutable layered template; a container is a running instance. Keep images small with slim bases, multi-stage builds, `.dockerignore`, and installing dependencies before copying source so layers cache well. Run as a non-root user.

## How do you handle database migrations?
Tags: databases

Use Alembic (SQLAlchemy) or Django migrations — versioned, reviewed scripts run in CI/CD before the new code. For zero downtime, use expand/contract: add nullable column → backfill → switch code → drop old column later.
