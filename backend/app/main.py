from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import SessionLocal, init_db
from app.routers import applications, dsa, followups, jobs, matching, prep, profile, progress, recruiters
from app.seed import run_seed

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    with SessionLocal() as db:
        run_seed(db, settings.prep_dir, demo=settings.seed_demo_data)
    yield


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

for module in (profile, jobs, matching, applications, recruiters, dsa, prep, followups, progress):
    app.include_router(module.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
