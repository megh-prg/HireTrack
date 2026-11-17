from typing import Annotated, TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.database.models import Profile, User

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
T = TypeVar("T")


def get_or_404(db: Session, model: type[T], item_id: int, user: User) -> T:
    """Fetch a row by id, but only if it belongs to this user."""
    item = db.get(model, item_id)
    if item is None or getattr(item, "user_id", None) != user.id:
        raise HTTPException(status_code=404, detail=f"{model.__name__} {item_id} not found")
    return item


def get_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
    return profile
