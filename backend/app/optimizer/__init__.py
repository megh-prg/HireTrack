"""Resume optimizer: ATS scoring, Gemini rewrite, and grounding.

Ported from the standalone ElevateCV project. Pure-Python scoring/grounding
plus synchronous Gemini calls, with no MongoDB/Redis/Celery dependency so it
fits HireTrack's Postgres + sync-router stack.
"""
