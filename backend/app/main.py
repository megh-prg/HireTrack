import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers import (
    applications,
    dsa,
    followups,
    jobs,
    matching,
    prep,
    profile,
    progress,
    recruiters,
    sources,
)
from app.seed import run_seed

settings = get_settings()
log = logging.getLogger("hiretrack")


def _refresh_sources() -> int:
    with SessionLocal() as db:
        return sources.refresh_stale(db, settings.auto_refresh_hours)


async def auto_refresh_loop() -> None:
    """Keep saved job sources fresh without anyone clicking Refresh."""
    await asyncio.sleep(30)  # let the app finish starting
    while True:
        try:
            ran = await asyncio.to_thread(_refresh_sources)
            if ran:
                log.info("Auto-refreshed %s job source(s)", ran)
        except Exception:  # never let a bad feed kill the loop
            log.exception("Auto-refresh failed")
        await asyncio.sleep(15 * 60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        run_seed(db, settings.prep_dir, demo=settings.seed_demo_data)
    task = asyncio.create_task(auto_refresh_loop()) if settings.auto_refresh_hours > 0 else None
    yield
    if task:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Job search and interview preparation platform: jobs, matching, applications, "
    "recruiters, DSA, interview prep, follow-ups and progress.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (profile, jobs, sources, matching, applications, recruiters, dsa, prep, followups, progress):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
