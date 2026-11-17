from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.auth import create_token, hash_password, verify_password
from app.config import get_settings
from app.database.models import User
from app.deps import DB, CurrentUser
from app.schemas import AuthIn, TokenOut, UserOut
from app.seed import seed_for_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/signup", response_model=TokenOut, status_code=201)
def signup(payload: AuthIn, db: DB):
    email = payload.email.lower().strip()
    if "@" not in email:
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    seed_for_user(db, user, settings.prep_dir)
    return TokenOut(token=create_token(user.id), email=user.email)


@router.post("/login", response_model=TokenOut)
def login(payload: AuthIn, db: DB):
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password.")
    return TokenOut(token=create_token(user.id), email=user.email)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut(id=user.id, email=user.email)
