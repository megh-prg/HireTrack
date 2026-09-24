"""Lightweight spaced repetition shared by DSA problems and prep questions.

Quality is self-rated 0-5 (0 = blank, 3 = got there with effort, 5 = instant recall).
A failed review (<3) resets the streak and brings the item back tomorrow.
"""

from datetime import date, timedelta

INTERVALS_DAYS = [1, 3, 7, 14, 30, 60]


def next_review(quality: int, streak: int, today: date) -> tuple[int, date]:
    if quality < 3:
        return 0, today + timedelta(days=1)
    streak += 1
    interval = INTERVALS_DAYS[min(streak - 1, len(INTERVALS_DAYS) - 1)]
    if quality == 3:
        interval = max(1, interval // 2)
    return streak, today + timedelta(days=interval)
