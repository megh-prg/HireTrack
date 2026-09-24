from fastapi import APIRouter

from app.deps import DB, get_profile
from app.jobs.matching import recompute_all
from app.schemas import ProfileBase, ProfileRead

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileRead)
def read_profile(db: DB):
    return get_profile(db)


@router.put("", response_model=ProfileRead)
def update_profile(payload: ProfileBase, db: DB):
    profile = get_profile(db)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    # Skills, roles and locations all feed the match score, so rescore everything.
    recompute_all(db, profile)
    return profile
