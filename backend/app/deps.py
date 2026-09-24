from typing import Annotated, TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Profile

DB = Annotated[Session, Depends(get_db)]
T = TypeVar("T")


def get_or_404(db: Session, model: type[T], item_id: int) -> T:
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} {item_id} not found")
    return item


def get_profile(db: Session) -> Profile:
    profile = db.get(Profile, 1)
    if profile is None:
        profile = Profile(id=1)
        db.add(profile)
        db.commit()
    return profile
