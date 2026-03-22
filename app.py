"""
Web UI for the candidate showcase. Order is shuffled on every page load.

Candidates can register (username + password), edit their profile, and upload a photo.

Run:
  uvicorn app:app --reload --host 0.0.0.0 --port 8000

Environment:
  SECRET_KEY       — session signing (required in production)
  CANDIDATES_DIR, AGGREGATE_JSON, DEMO_MODE, NO_SHUFFLE — same as before
"""

from __future__ import annotations

import os
import random
from pathlib import Path

from fastapi import FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from auth_password import hash_password, validate_username, verify_password
from profile import JobSeekerProfile, load_profile_by_username, save_profile_to_path
from profile_search import filter_profiles_by_query
from profile_form import (
    experience_from_form,
    experience_slots_for_template,
    experience_slots_from_form,
    link_slots_for_template,
    link_slots_from_form,
    links_from_form,
)
from showcase import collect_profiles, _script_dir

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "static" / "uploads"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024

LOGIN_ERRORS = {
    "invalid_username": "Username must be 3–32 characters: lowercase letters, digits, underscore.",
    "bad_credentials": "Invalid username or password.",
    "missing_profile": "Profile file missing. Register again or contact support.",
}
REGISTER_ERRORS = {
    "invalid_username": LOGIN_ERRORS["invalid_username"],
    "password_mismatch": "Passwords do not match.",
    "password_short": "Password must be at least 8 characters.",
    "taken": "That username is already registered.",
    "invalid_video_url": "Video link must start with https:// or http://",
}
ACCOUNT_ERRORS = {
    "bad_current_password": "Current password is incorrect.",
    "password_short": "New password must be at least 8 characters.",
    "no_password_set": "Set a password via register first.",
    "upload_too_large": "Image must be 2 MB or smaller.",
    "invalid_image": "Upload a JPEG, PNG, GIF, or WebP image.",
}

templates = Jinja2Templates(directory=str(ROOT / "templates"))

app = FastAPI(title="Candidate showcase")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get(
        "SECRET_KEY",
        "dev-insecure-change-me-use-os-environ-secret-key-32chars-min",
    ),
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def _candidates_dir() -> Path:
    raw = os.environ.get("CANDIDATES_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    return _script_dir() / "candidates"


def _aggregate_path() -> Path | None:
    raw = os.environ.get("AGGREGATE_JSON")
    if not raw:
        return None
    return Path(raw).expanduser().resolve()


def _guess_image_ext(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _delete_uploads_for_username(username: str) -> None:
    if not UPLOAD_DIR.is_dir():
        return
    for p in UPLOAD_DIR.glob(f"{username}.*"):
        if p.is_file():
            p.unlink()


def _load_profiles_unshuffled() -> list:
    demo = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")
    return collect_profiles(
        candidates_dir=_candidates_dir(),
        aggregate_json=_aggregate_path(),
        demo_builtin_only=demo,
    )


def _should_shuffle() -> bool:
    return not os.environ.get("NO_SHUFFLE", "").lower() in ("1", "true", "yes")


def _parse_optional_video_url(raw: str | None) -> tuple[str | None, str | None]:
    """
    Returns (url_or_none, error_message_or_none).
    Empty input is valid (no video). Non-empty must be http(s).
    """
    s = (raw or "").strip()
    if not s:
        return None, None
    if s.lower().startswith(("https://", "http://")):
        return s, None
    return None, "Self-introduction video link must start with https:// or http://"


def _profile_to_dict(p: JobSeekerProfile) -> dict:
    """Public JSON (no password)."""
    return {
        "username": p.username,
        "name": p.name,
        "headline": p.headline,
        "usp": p.usp,
        "photo": p.photo,
        "self_intro_video_url": p.self_intro_video_url,
        "usp_proof_points": list(p.usp_proof_points),
        "skills": list(p.skills),
        "experience": [
            {
                "title": j.title,
                "company": j.company,
                "period": j.period,
                "highlights": list(j.highlights),
            }
            for j in p.experience
        ],
        "education": list(p.education),
        "links": dict(p.links),
        "extras": {k: list(v) for k, v in (p.extras or {}).items()},
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, q: str | None = Query(None)) -> HTMLResponse:
    all_profiles = _load_profiles_unshuffled()
    total_count = len(all_profiles)
    q_clean = (q or "").strip()
    candidates = filter_profiles_by_query(all_profiles, q_clean)
    if _should_shuffle() and len(candidates) > 1:
        random.shuffle(candidates)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "candidates": candidates,
            "search_query": q_clean,
            "total_count": total_count,
            "filtered_count": len(candidates),
            "is_search": bool(q_clean),
            "shuffle_note": len(candidates) > 1 and _should_shuffle(),
        },
    )


@app.get("/api/candidates")
async def api_candidates(q: str | None = Query(None)) -> JSONResponse:
    all_profiles = _load_profiles_unshuffled()
    filtered = filter_profiles_by_query(all_profiles, q)
    if _should_shuffle() and len(filtered) > 1:
        random.shuffle(filtered)
    return JSONResponse(
        {
            "candidates": [_profile_to_dict(p) for p in filtered],
            "query": (q or "").strip(),
            "total": len(all_profiles),
            "count": len(filtered),
        }
    )


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request) -> HTMLResponse:
    code = request.query_params.get("error")
    err_msg = None
    if code:
        err_msg = LOGIN_ERRORS.get(code, code.replace("_", " "))
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error_message": err_msg},
    )


@app.post("/login")
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    username = username.strip().lower()
    if not validate_username(username):
        return RedirectResponse("/login?error=invalid_username", status_code=303)
    prof = load_profile_by_username(_candidates_dir(), username)
    if not prof or not prof.password_hash:
        return RedirectResponse("/login?error=bad_credentials", status_code=303)
    if not verify_password(password, prof.password_hash):
        return RedirectResponse("/login?error=bad_credentials", status_code=303)
    request.session["username"] = username
    return RedirectResponse("/account", status_code=303)


@app.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request) -> HTMLResponse:
    code = request.query_params.get("error")
    err_msg = None
    if code:
        err_msg = REGISTER_ERRORS.get(code, code.replace("_", " "))
    return templates.TemplateResponse(
        "register.html",
        {"request": request, "error_message": err_msg},
    )


@app.post("/register", response_model=None)
async def register_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    name: str = Form(...),
    headline: str = Form(...),
    usp: str = Form(...),
    skills: str = Form(""),
    self_intro_video_url: str = Form(""),
) -> RedirectResponse:
    username = username.strip().lower()
    if not validate_username(username):
        return RedirectResponse("/register?error=invalid_username", status_code=303)
    if password != password_confirm:
        return RedirectResponse("/register?error=password_mismatch", status_code=303)
    if len(password) < 8:
        return RedirectResponse("/register?error=password_short", status_code=303)
    base = _candidates_dir()
    if load_profile_by_username(base, username):
        return RedirectResponse("/register?error=taken", status_code=303)

    intro_url, v_err = _parse_optional_video_url(self_intro_video_url)
    if v_err:
        return RedirectResponse("/register?error=invalid_video_url", status_code=303)

    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    prof = JobSeekerProfile(
        name=name.strip(),
        headline=headline.strip(),
        usp=usp.strip(),
        skills=skill_list,
        username=username,
        password_hash=hash_password(password),
        profile_path=base / username / "profile.json",
        self_intro_video_url=intro_url,
    )
    save_profile_to_path(prof.profile_path, prof)
    request.session["username"] = username
    request.session["flash_welcome"] = True
    return RedirectResponse("/account", status_code=303)


@app.get("/account", response_class=HTMLResponse, response_model=None)
async def account_get(request: Request) -> HTMLResponse | RedirectResponse:
    username = request.session.get("username")
    if not username or not isinstance(username, str):
        return RedirectResponse("/login", status_code=303)
    prof = load_profile_by_username(_candidates_dir(), username)
    if not prof or not prof.profile_path:
        request.session.clear()
        return RedirectResponse("/login?error=missing_profile", status_code=303)

    err_code = request.query_params.get("error")
    error_message = None
    if err_code:
        error_message = ACCOUNT_ERRORS.get(err_code, err_code.replace("_", " "))
    saved = request.query_params.get("saved") == "1"
    welcome = bool(request.session.pop("flash_welcome", None))

    return templates.TemplateResponse(
        "account.html",
        {
            "request": request,
            "profile": prof,
            "name": prof.name,
            "headline": prof.headline,
            "usp": prof.usp,
            "experience_slots": experience_slots_for_template(prof.experience),
            "link_slots": link_slots_for_template(prof.links),
            "usp_proof_text": "\n".join(prof.usp_proof_points),
            "skills_text": ", ".join(prof.skills),
            "education_text": "\n".join(prof.education),
            "self_intro_video_url": prof.self_intro_video_url or "",
            "error_message": error_message,
            "saved": saved,
            "welcome": welcome,
        },
    )


@app.post("/account", response_model=None)
async def account_post(request: Request) -> RedirectResponse | HTMLResponse:
    username = request.session.get("username")
    if not username or not isinstance(username, str):
        return RedirectResponse("/login", status_code=303)

    prof = load_profile_by_username(_candidates_dir(), username)
    if not prof or not prof.profile_path:
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    form = await request.form()
    name = (form.get("name") or "").strip()
    headline = (form.get("headline") or "").strip()
    usp = (form.get("usp") or "").strip()
    usp_proof_points = (form.get("usp_proof_points") or "").strip()
    skills = (form.get("skills") or "").strip()
    education = (form.get("education") or "").strip()
    intro_url, intro_err = _parse_optional_video_url(form.get("self_intro_video_url"))
    current_password = (form.get("current_password") or "").strip()
    new_password = (form.get("new_password") or "").strip()
    remove_photo = form.get("remove_photo")

    if not name or not headline or not usp:
        return templates.TemplateResponse(
            "account.html",
            {
                "request": request,
                "profile": prof,
                "name": name,
                "headline": headline,
                "usp": usp,
                "experience_slots": experience_slots_from_form(form),
                "link_slots": link_slots_from_form(form),
                "usp_proof_text": usp_proof_points,
                "skills_text": skills,
                "education_text": education,
                "self_intro_video_url": (form.get("self_intro_video_url") or "").strip(),
                "error_message": "Please fill in your name, headline, and unique value (USP).",
                "saved": False,
                "welcome": False,
            },
            status_code=400,
        )

    if intro_err:
        return templates.TemplateResponse(
            "account.html",
            {
                "request": request,
                "profile": prof,
                "name": name,
                "headline": headline,
                "usp": usp,
                "experience_slots": experience_slots_from_form(form),
                "link_slots": link_slots_from_form(form),
                "usp_proof_text": usp_proof_points,
                "skills_text": skills,
                "education_text": education,
                "self_intro_video_url": (form.get("self_intro_video_url") or "").strip(),
                "error_message": intro_err,
                "saved": False,
                "welcome": False,
            },
            status_code=400,
        )

    experience = experience_from_form(form)
    links = links_from_form(form)
    usp_lines = [ln.strip() for ln in usp_proof_points.splitlines() if ln.strip()]
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    edu_lines = [ln.strip() for ln in education.splitlines() if ln.strip()]

    new_hash = prof.password_hash
    if new_password:
        if not prof.password_hash:
            return RedirectResponse("/account?error=no_password_set", status_code=303)
        if not current_password or not verify_password(current_password, prof.password_hash):
            return RedirectResponse("/account?error=bad_current_password", status_code=303)
        if len(new_password) < 8:
            return RedirectResponse("/account?error=password_short", status_code=303)
        new_hash = hash_password(new_password)

    photo_url = prof.photo
    if remove_photo:
        _delete_uploads_for_username(username)
        photo_url = None

    photo = form.get("photo")
    if isinstance(photo, UploadFile) and photo.filename:
        body = await photo.read()
        if len(body) > MAX_UPLOAD_BYTES:
            return RedirectResponse("/account?error=upload_too_large", status_code=303)
        ext = _guess_image_ext(body)
        if not ext:
            return RedirectResponse("/account?error=invalid_image", status_code=303)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        _delete_uploads_for_username(username)
        dest = UPLOAD_DIR / f"{username}.{ext}"
        dest.write_bytes(body)
        photo_url = f"/static/uploads/{username}.{ext}"

    updated = JobSeekerProfile(
        name=name,
        headline=headline,
        usp=usp,
        usp_proof_points=usp_lines,
        skills=skill_list,
        experience=experience,
        education=edu_lines,
        links=links,
        extras=dict(prof.extras or {}),
        username=prof.username,
        password_hash=new_hash,
        photo=photo_url,
        self_intro_video_url=intro_url,
        profile_path=prof.profile_path,
    )
    save_profile_to_path(updated.profile_path, updated)
    return RedirectResponse("/account?saved=1", status_code=303)
