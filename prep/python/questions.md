# Python

## What is the GIL and when does it matter?
Tags: concurrency, cpython

- The Global Interpreter Lock lets only one thread execute Python bytecode at a time in CPython.
- **I/O-bound** work (HTTP calls, DB queries) still benefits from threads because the GIL is released while waiting.
- **CPU-bound** work does not; use `multiprocessing`, `concurrent.futures.ProcessPoolExecutor`, or push the work into C extensions (NumPy) that release the GIL.
- Python 3.13+ ships an optional free-threaded build (PEP 703), but most production deployments still run with the GIL.

## Explain `async`/`await`. When is asyncio the right tool?
Tags: asyncio, concurrency

- A coroutine (`async def`) pauses at `await` and hands control back to the event loop, so one thread can juggle thousands of waiting I/O operations.
- Great for many concurrent network calls: API gateways, calling LLM APIs in parallel, websockets.
- Wrong tool for CPU-heavy code: it blocks the loop. Offload with `asyncio.to_thread` or a process pool.
- Common bug: calling a blocking library (e.g. `requests`, a sync DB driver) inside an async endpoint — it stalls every request.

## What are generators and why use them?
Tags: generators, memory

- Functions that `yield` values lazily and keep their state between calls.
- Memory stays constant regardless of input size — ideal for streaming large files, paginated APIs, or LLM token streams.
- `yield from` delegates to a sub-generator; generator expressions `(x for x in ...)` are the inline form.

## How do decorators work? Write one that times a function.
Tags: decorators, functions

A decorator is a callable that takes a function and returns a new one.

```python
import functools, time

def timed(fn):
    @functools.wraps(fn)          # keeps __name__, __doc__
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            print(f"{fn.__name__} took {time.perf_counter() - start:.3f}s")
    return wrapper
```

Mention `functools.wraps` and that decorators with arguments need one more layer of nesting.

## Mutable default arguments — what's the bug?
Tags: gotchas

`def add(item, items=[])` evaluates `[]` once at definition time, so every call shares the same list. Use `items=None` then `items = items or []` (or `if items is None`).

## Difference between a list, tuple, set and dict — and their complexities?
Tags: data structures

- list: ordered, mutable; index O(1), `in` O(n), append amortised O(1).
- tuple: ordered, immutable, hashable if its items are — usable as dict keys.
- set: unordered unique items; `in` O(1) average.
- dict: insertion-ordered key→value; get/set/`in` O(1) average.

## What are context managers? How would you write one?
Tags: resources

They guarantee setup/teardown with `with`. Implement `__enter__`/`__exit__`, or use `contextlib.contextmanager`:

```python
from contextlib import contextmanager

@contextmanager
def transaction(conn):
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

## `is` vs `==`?
Tags: gotchas

`==` compares values (`__eq__`); `is` compares identity (same object). Use `is` only for singletons like `None`. Small ints and interned strings can make `is` look like it works — it's an implementation detail.

## Shallow vs deep copy?
Tags: data structures

`copy.copy` / `list[:]` copies the outer container but shares nested objects; `copy.deepcopy` recursively copies everything. Bugs appear when you mutate a nested list after a shallow copy.

## How does Python manage memory?
Tags: cpython, memory

Reference counting frees most objects immediately; a cyclic garbage collector handles reference cycles. `__slots__` reduces per-instance memory. Use `tracemalloc` to find leaks.

## What are type hints good for if Python doesn't enforce them?
Tags: typing

Static checking with mypy/pyright, better IDE support, and runtime validation in libraries like Pydantic and FastAPI (request parsing, OpenAPI docs). Mention `Optional`/`X | None`, generics, `Protocol`, and `TypedDict`.

## Explain `*args` and `**kwargs`, and keyword-only arguments.
Tags: functions

`*args` collects extra positional args into a tuple, `**kwargs` extra keyword args into a dict. Parameters after a bare `*` are keyword-only (`def f(a, *, strict=False)`); parameters before `/` are positional-only.
