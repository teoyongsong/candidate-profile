"""Job-seeker profile model — edit SAMPLE_PROFILE to match your story."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Login usernames: lowercase letters, digits, underscore (matches folder names)
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


@dataclass
class Experience:
    """One role on the timeline."""

    title: str
    company: str
    period: str
    highlights: list[str]


@dataclass
class JobSeekerProfile:
    """Structured profile with an explicit USP the UI can emphasize."""

    name: str
    headline: str
    # Unique Selling Proposition: one sharp sentence — what only you bring
    usp: str
    # 2–4 bullets that prove the USP (metrics, scope, outcomes)
    usp_proof_points: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    experience: list[Experience] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    links: dict[str, str] = field(default_factory=dict)
    # Optional extra sections as label -> lines
    extras: dict[str, list[str]] = field(default_factory=dict)
    # Account (optional — set via web register / JSON)
    username: str | None = None
    password_hash: str | None = None  # bcrypt; never expose in public API
    # Public URL path, e.g. /static/uploads/jane.jpg
    photo: str | None = None
    # Link to self-intro video (Loom, YouTube, Vimeo, etc.)
    self_intro_video_url: str | None = None
    # Set when loaded from disk (not stored in JSON)
    profile_path: Path | None = field(default=None, repr=False)


# --- Sample data: multiple candidates (edit or load from JSON) ----------------------

SAMPLE_PROFILE = JobSeekerProfile(
    name="Alex Chen",
    headline="Data Engineer · Analytics & ML-ready pipelines",
    usp=(
        "I ship reliable, observable data products that turn messy business "
        "questions into dashboards and models teams actually use — not shelf-ware."
    ),
    usp_proof_points=[
        "Cut pipeline incident time by 60% with idempotent jobs, tests, and alerting",
        "Owned end-to-end: ingestion → warehouse → dbt → BI for a 40-person org",
        "Comfortable across SQL, Python, Spark, and cloud (AWS/GCP basics)",
    ],
    skills=[
        "Python",
        "SQL",
        "dbt",
        "Airflow / Dagster",
        "Spark",
        "BigQuery / Snowflake",
        "AWS & GCP",
    ],
    experience=[
        Experience(
            title="Senior Data Engineer",
            company="Example Analytics Co.",
            period="2022 — present",
            highlights=[
                "Designed batch + near-real-time pipelines for product and finance KPIs",
                "Mentored two juniors on testing and CI for data repos",
            ],
        ),
        Experience(
            title="Data Engineer",
            company="Earlier Startup Ltd.",
            period="2019 — 2022",
            highlights=[
                "Migrated legacy ETL to cloud-native stack; reduced run cost ~35%",
            ],
        ),
    ],
    education=[
        "B.Sc. Computer Science — Example University",
    ],
    links={
        "GitHub": "https://github.com/example",
        "LinkedIn": "https://linkedin.com/in/example",
    },
)

SAMPLE_CANDIDATES: list[JobSeekerProfile] = [
    SAMPLE_PROFILE,
    JobSeekerProfile(
        name="Jordan Rivera",
        headline="Backend Engineer · APIs, reliability, and clear ownership",
        usp=(
            "I own services from design to on-call: clear APIs, measurable SLOs, "
            "and runbooks that mean incidents get shorter every time."
        ),
        usp_proof_points=[
            "Led migration of monolith checkout slice to Go microservice; p99 −40%",
            "Introduced feature flags + gradual rollout for risky releases",
            "On-call primary for payments; MTTR down from hours to <30 min",
        ],
        skills=[
            "Go",
            "Python",
            "PostgreSQL",
            "Kubernetes",
            "gRPC",
            "Observability (Prometheus/Grafana)",
        ],
        experience=[
            Experience(
                title="Staff Backend Engineer",
                company="Payments Platform Inc.",
                period="2021 — present",
                highlights=[
                    "Designed idempotent payment APIs used by 3 product teams",
                    "Championed SLO-based alerting and error-budget reviews",
                ],
            ),
        ],
        education=["M.Eng. Software Systems — Example Institute"],
        links={
            "GitHub": "https://github.com/example-jordan",
            "LinkedIn": "https://linkedin.com/in/example-jordan",
        },
    ),
]


def profile_from_dict(data: dict[str, Any]) -> JobSeekerProfile:
    """Build a profile from a dict (e.g. loaded from JSON later)."""
    exp_raw = data.get("experience") or []
    experience = [
        Experience(
            title=e["title"],
            company=e["company"],
            period=e["period"],
            highlights=list(e.get("highlights") or []),
        )
        for e in exp_raw
    ]
    return JobSeekerProfile(
        name=data["name"],
        headline=data["headline"],
        usp=data["usp"],
        usp_proof_points=list(data.get("usp_proof_points") or []),
        skills=list(data.get("skills") or []),
        experience=experience,
        education=list(data.get("education") or []),
        links=dict(data.get("links") or {}),
        extras={k: list(v) for k, v in (data.get("extras") or {}).items()},
        username=data.get("username"),
        password_hash=data.get("password_hash"),
        photo=data.get("photo"),
        self_intro_video_url=data.get("self_intro_video_url"),
    )


def username_from_filename_stem(stem: str) -> str | None:
    """Use file stem as username only if it matches USERNAME_RE."""
    if USERNAME_RE.match(stem):
        return stem
    return None


def serialize_profile_for_disk(p: JobSeekerProfile) -> dict[str, Any]:
    """JSON-serializable dict for writing profile.json (includes password_hash when set)."""
    d: dict[str, Any] = {
        "name": p.name,
        "headline": p.headline,
        "usp": p.usp,
        "usp_proof_points": list(p.usp_proof_points),
        "skills": list(p.skills),
        "experience": [
            {
                "title": e.title,
                "company": e.company,
                "period": e.period,
                "highlights": list(e.highlights),
            }
            for e in p.experience
        ],
        "education": list(p.education),
        "links": dict(p.links),
        "extras": {k: list(v) for k, v in (p.extras or {}).items()},
    }
    if p.username:
        d["username"] = p.username
    if p.password_hash:
        d["password_hash"] = p.password_hash
    if p.photo:
        d["photo"] = p.photo
    if p.self_intro_video_url:
        d["self_intro_video_url"] = p.self_intro_video_url
    return d


def save_profile_to_path(path: Path, p: JobSeekerProfile) -> None:
    """Write profile to JSON file (creates parent dirs)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = serialize_profile_for_disk(p)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def profiles_from_json_payload(raw: Any) -> list[JobSeekerProfile]:
    """
    Parse JSON as either:
    - a list of profile objects,
    - {"candidates": [ ... ]},
    - or a single profile object (wrapped as a one-item list).
    """
    if isinstance(raw, list):
        return [profile_from_dict(x) for x in raw]
    if isinstance(raw, dict):
        if "candidates" in raw:
            return [profile_from_dict(x) for x in raw["candidates"]]
        return [profile_from_dict(raw)]
    raise TypeError("JSON root must be a list, object, or {candidates: [...]}")


def single_profile_from_json_file(path: Path) -> JobSeekerProfile:
    """
    Load exactly one profile from a JSON file (for candidates/your-name.json).

    Accepts a single object or a single-element array. Rejects aggregate files
    that use a top-level 'candidates' key — use one profile per file.
    """
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        if len(raw) != 1:
            raise ValueError(
                "expected one profile object or a single-element array in this file"
            )
        raw = raw[0]
    if not isinstance(raw, dict):
        raise ValueError("expected a JSON object at the root of this file")
    if "candidates" in raw:
        raise ValueError(
            "use one profile per file — remove the 'candidates' wrapper "
            "(see profile.example.json for a multi-candidate aggregate format)"
        )
    return profile_from_dict(raw)


def load_profiles_from_directory(directory: Path) -> tuple[list[JobSeekerProfile], list[str]]:
    """
    Load profiles from:

    - ``directory/*.json`` (one profile per file, sorted by name)
    - ``directory/<username>/profile.json`` (self-managed accounts)

    Duplicate usernames are skipped (first wins). Sets ``profile_path`` on each profile.
    """
    profiles: list[JobSeekerProfile] = []
    errors: list[str] = []
    seen_usernames: set[str] = set()
    if not directory.is_dir():
        return profiles, errors

    def try_add(path: Path) -> None:
        try:
            prof = single_profile_from_json_file(path)
            prof.profile_path = path
            if not prof.username:
                prof.username = username_from_filename_stem(path.parent.name) if path.name == "profile.json" else username_from_filename_stem(path.stem)
            if prof.username:
                if prof.username in seen_usernames:
                    errors.append(f"{path}: skipped duplicate username '{prof.username}'")
                    return
                seen_usernames.add(prof.username)
            profiles.append(prof)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: {exc}")

    for path in sorted(directory.glob("*.json")):
        try_add(path)

    for subdir in sorted(p for p in directory.iterdir() if p.is_dir()):
        pfile = subdir / "profile.json"
        if pfile.is_file():
            try_add(pfile)

    return profiles, errors


def load_profile_by_username(candidates_dir: Path, username: str) -> JobSeekerProfile | None:
    """Load a single profile for login / account editing."""
    sub = candidates_dir / username / "profile.json"
    if sub.is_file():
        try:
            p = single_profile_from_json_file(sub)
            p.profile_path = sub
            if not p.username:
                p.username = username
            return p
        except Exception:
            return None
    for path in sorted(candidates_dir.glob("*.json")):
        try:
            p = single_profile_from_json_file(path)
            p.profile_path = path
            if p.username == username:
                return p
        except Exception:
            continue
    return None
