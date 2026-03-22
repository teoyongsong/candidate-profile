"""Keyword search across public profile fields (for employer filtering)."""

from __future__ import annotations

import re

from profile import JobSeekerProfile


def _query_tokens(query: str) -> list[str]:
    q = query.strip()
    if not q:
        return []
    return [t for t in re.split(r"\s+", q) if t]


def profile_searchable_text(p: JobSeekerProfile) -> str:
    """Flatten profile content for case-insensitive substring matching."""
    parts: list[str] = [
        p.name or "",
        p.headline or "",
        p.usp or "",
        " ".join(p.usp_proof_points or []),
        " ".join(p.skills or []),
        " ".join(p.education or []),
    ]
    if p.username:
        parts.append(p.username)
    if p.self_intro_video_url:
        parts.append(p.self_intro_video_url)
    for e in p.experience or []:
        parts.extend(
            [
                e.title,
                e.company,
                e.period,
                " ".join(e.highlights or []),
            ]
        )
    for label, url in (p.links or {}).items():
        parts.extend([label, url])
    for section, lines in (p.extras or {}).items():
        parts.append(section)
        parts.extend(lines or [])
    return " ".join(parts).lower()


def profile_matches_keywords(p: JobSeekerProfile, query: str) -> bool:
    """
    True if every whitespace-separated token in ``query`` appears somewhere
    in the profile (AND semantics). Empty query matches all.
    """
    tokens = _query_tokens(query)
    if not tokens:
        return True
    hay = profile_searchable_text(p)
    return all(t.lower() in hay for t in tokens)


def filter_profiles_by_query(
    profiles: list[JobSeekerProfile],
    query: str | None,
) -> list[JobSeekerProfile]:
    q = (query or "").strip()
    if not q:
        return list(profiles)
    return [p for p in profiles if profile_matches_keywords(p, q)]
