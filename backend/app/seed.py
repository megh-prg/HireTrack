"""Seed a new user's interview-prep content from /prep. Safe to run repeatedly per user."""

import csv
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Difficulty, DSAProblem, PrepQuestion, Profile, User
from app.schemas import PREP_TRACKS

QUESTION_HEADING = re.compile(r"^##\s+(.+?)\s*$", re.M)
TAGS_LINE = re.compile(r"^tags:\s*(.+)$", re.I | re.M)


def parse_questions(markdown: str) -> list[dict]:
    """`## Question` headings; everything until the next heading is the model answer."""
    matches = list(QUESTION_HEADING.finditer(markdown))
    questions = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[match.end():end].strip()
        tags: list[str] = []
        if tag_match := TAGS_LINE.search(body):
            tags = [t.strip() for t in tag_match.group(1).split(",") if t.strip()]
            body = TAGS_LINE.sub("", body).strip()
        questions.append({"question": match.group(1), "answer": body, "tags": tags})
    return questions


def seed_prep(db: Session, user_id: int, prep_dir: Path) -> int:
    existing = set(
        db.execute(
            select(PrepQuestion.track, PrepQuestion.question).where(PrepQuestion.user_id == user_id)
        ).tuples()
    )
    added = 0
    for track in PREP_TRACKS:
        path = prep_dir / track / "questions.md"
        if not path.exists():
            continue
        for q in parse_questions(path.read_text(encoding="utf-8")):
            if (track, q["question"]) in existing:
                continue
            db.add(PrepQuestion(user_id=user_id, track=track, **q))
            added += 1
    db.commit()
    return added


def seed_dsa(db: Session, user_id: int, prep_dir: Path) -> int:
    path = prep_dir / "dsa" / "problems.csv"
    if not path.exists():
        return 0
    existing = set(db.scalars(select(DSAProblem.title).where(DSAProblem.user_id == user_id)))
    added = 0
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row["title"] in existing:
                continue
            db.add(
                DSAProblem(
                    user_id=user_id,
                    title=row["title"],
                    topic=row["topic"],
                    difficulty=Difficulty(row["difficulty"].lower()),
                    url=row.get("url", ""),
                )
            )
            added += 1
    db.commit()
    return added


def seed_for_user(db: Session, user: User, prep_dir: Path) -> None:
    """Give a brand-new user an empty profile and their own copy of the prep catalog."""
    if db.scalar(select(Profile).where(Profile.user_id == user.id)) is None:
        db.add(Profile(user_id=user.id))
        db.commit()
    seed_prep(db, user.id, prep_dir)
    seed_dsa(db, user.id, prep_dir)
