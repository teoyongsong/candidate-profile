"""
Candidate profile showcase — Streamlit UI.

Run locally:
  streamlit run streamlit_app.py

Deploy: Streamlit Community Cloud — set main file to streamlit_app.py
Uses the same candidates/ JSON and bcrypt auth as the FastAPI app.
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import streamlit as st

from auth_password import hash_password, validate_username, verify_password
from profile import Experience, JobSeekerProfile, load_profile_by_username, save_profile_to_path
from profile_form import (
    MAX_EXPERIENCE_ROWS,
    MAX_LINK_ROWS,
    experience_slots_for_template,
    link_slots_for_template,
)
from profile_search import filter_profiles_by_query
from showcase import collect_profiles, _script_dir

ROOT = Path(__file__).resolve().parent
UPLOAD_DIR = ROOT / "static" / "uploads"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


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


def load_profiles_unshuffled() -> list:
    demo = os.environ.get("DEMO_MODE", "").lower() in ("1", "true", "yes")
    return collect_profiles(
        candidates_dir=_candidates_dir(),
        aggregate_json=_aggregate_path(),
        demo_builtin_only=demo,
    )


def should_shuffle() -> bool:
    return not os.environ.get("NO_SHUFFLE", "").lower() in ("1", "true", "yes")


def parse_optional_video_url(raw: str | None) -> tuple[str | None, str | None]:
    s = (raw or "").strip()
    if not s:
        return None, None
    if s.lower().startswith(("https://", "http://")):
        return s, None
    return None, "Video link must start with https:// or http://"


def guess_image_ext(data: bytes) -> str | None:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def delete_uploads_for_username(username: str) -> None:
    if not UPLOAD_DIR.is_dir():
        return
    for p in UPLOAD_DIR.glob(f"{username}.*"):
        if p.is_file():
            p.unlink()


def local_image_path(photo_url: str | None) -> Path | None:
    if not photo_url or not photo_url.startswith("/static/"):
        return None
    rel = photo_url.lstrip("/").replace("/", os.sep)
    path = ROOT / rel
    return path if path.is_file() else None


def init_session() -> None:
    if "username" not in st.session_state:
        st.session_state.username = None


def page_showcase() -> None:
    st.title("Tech candidate showcase")
    st.caption(
        "For employers: filter by skills, tools, or keywords. "
        "All words must appear somewhere in the profile."
    )

    q = st.text_input(
        "Search profiles",
        placeholder="e.g. Python AWS backend",
        key="search_q",
    )
    profiles = load_profiles_unshuffled()
    if q.strip():
        profiles = filter_profiles_by_query(profiles, q)
    total = len(load_profiles_unshuffled())
    st.caption(f"Showing **{len(profiles)}** of **{total}** candidates" + (f' for “{q.strip()}”' if q.strip() else ""))

    if should_shuffle() and len(profiles) > 1:
        random.shuffle(profiles)

    if not profiles:
        st.warning("No matching candidates. Try different keywords.")
        return

    for p in profiles:
        with st.container():
            st.divider()
            head_cols = st.columns([1, 4]) if p.photo else st.columns([1])
            with head_cols[0]:
                lp = local_image_path(p.photo)
                if lp:
                    st.image(str(lp), width=96)
            with head_cols[-1]:
                st.subheader(p.name)
                st.caption(p.headline)

            if p.self_intro_video_url:
                st.link_button("Watch self-introduction", p.self_intro_video_url, use_container_width=False)

            st.markdown("**Unique value**")
            st.write(p.usp)
            if p.usp_proof_points:
                for pt in p.usp_proof_points:
                    st.markdown(f"- {pt}")

            if p.skills:
                st.markdown("**Skills**")
                st.write(", ".join(p.skills))

            if p.experience:
                st.markdown("**Experience**")
                for job in p.experience:
                    st.markdown(f"**{job.title}** — {job.company} · *{job.period}*")
                    for h in job.highlights:
                        st.markdown(f"- {h}")

            if p.education:
                st.markdown("**Education**")
                for line in p.education:
                    st.markdown(f"- {line}")

            if p.links:
                st.markdown("**Links**")
                for label, url in p.links.items():
                    st.markdown(f"- [{label}]({url})")


def page_login() -> None:
    st.title("Log in")
    with st.form("login"):
        u = st.text_input("Username", autocomplete="username")
        pw = st.text_input("Password", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Log in")
    if ok:
        username = u.strip().lower()
        if not validate_username(username):
            st.error("Invalid username format.")
            return
        prof = load_profile_by_username(_candidates_dir(), username)
        if not prof or not prof.password_hash or not verify_password(pw, prof.password_hash):
            st.error("Invalid username or password.")
            return
        st.session_state.username = username
        st.success("Logged in.")
        st.rerun()


def page_register() -> None:
    st.title("Create your profile")
    st.markdown(
        "Record a video intro with [Loom](https://www.loom.com), "
        "[YouTube](https://www.youtube.com/upload), or [Vimeo](https://vimeo.com/upload), then paste the link."
    )
    with st.form("reg"):
        uname = st.text_input("Username (lowercase, digits, underscore)", max_chars=32)
        pw = st.text_input("Password (min 8 characters)", type="password")
        pw2 = st.text_input("Confirm password", type="password")
        name = st.text_input("Full name")
        headline = st.text_input("Professional headline")
        usp = st.text_area("Unique value (USP)", height=120)
        skills = st.text_input("Skills (optional, comma-separated)", "")
        video = st.text_input("Self-intro video URL (optional)", placeholder="https://…")
        submitted = st.form_submit_button("Register")
    if not submitted:
        return
    username = uname.strip().lower()
    if not validate_username(username):
        st.error("Username must be 3–32 characters: a-z, 0-9, underscore.")
        return
    if pw != pw2:
        st.error("Passwords do not match.")
        return
    if len(pw) < 8:
        st.error("Password must be at least 8 characters.")
        return
    base = _candidates_dir()
    if load_profile_by_username(base, username):
        st.error("That username is already taken.")
        return
    intro_url, verr = parse_optional_video_url(video)
    if verr:
        st.error(verr)
        return
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    prof = JobSeekerProfile(
        name=name.strip(),
        headline=headline.strip(),
        usp=usp.strip(),
        skills=skill_list,
        username=username,
        password_hash=hash_password(pw),
        profile_path=base / username / "profile.json",
        self_intro_video_url=intro_url,
    )
    save_profile_to_path(prof.profile_path, prof)
    st.session_state.username = username
    st.success("Registered. You can edit your full profile under **My profile**.")
    st.rerun()


def page_account() -> None:
    username = st.session_state.username
    if not username:
        st.warning("Log in first.")
        return
    prof = load_profile_by_username(_candidates_dir(), username)
    if not prof or not prof.profile_path:
        st.error("Profile file missing.")
        st.session_state.username = None
        st.rerun()
        return

    st.title("My profile")
    slots = experience_slots_for_template(prof.experience)
    link_slots = link_slots_for_template(prof.links)

    up = st.file_uploader("Photo (JPEG, PNG, GIF, WebP · max 2 MB)", type=["jpg", "jpeg", "png", "gif", "webp"])
    remove_photo = st.checkbox("Remove current photo", value=False)

    with st.form("account"):
        st.subheader("Self-introduction video")
        st.markdown(
            "[Loom](https://www.loom.com) · [YouTube](https://www.youtube.com/upload) · [Vimeo](https://vimeo.com/upload)"
        )
        video_url = st.text_input(
            "Video page URL (optional)",
            value=prof.self_intro_video_url or "",
        )
        st.subheader("Basics")
        name = st.text_input("Name", value=prof.name)
        headline = st.text_input("Headline", value=prof.headline)
        usp = st.text_area("USP", value=prof.usp, height=100)
        usp_proof = st.text_area(
            "USP proof (one per line)",
            value="\n".join(prof.usp_proof_points),
            height=100,
        )
        skills = st.text_input("Skills (comma-separated)", value=", ".join(prof.skills))
        education = st.text_area("Education (one per line)", value="\n".join(prof.education), height=80)

        st.subheader("Experience")
        exp_titles: list[str] = []
        exp_companies: list[str] = []
        exp_periods: list[str] = []
        exp_highlights: list[str] = []
        for i in range(MAX_EXPERIENCE_ROWS):
            s = slots[i] if i < len(slots) else {"title": "", "company": "", "period": "", "highlights": ""}
            st.markdown(f"**Role {i + 1}**")
            exp_titles.append(st.text_input("Title", value=s["title"], key=f"et{i}"))
            exp_companies.append(st.text_input("Company", value=s["company"], key=f"ec{i}"))
            exp_periods.append(st.text_input("Period", value=s["period"], key=f"ep{i}"))
            exp_highlights.append(
                st.text_area("Highlights (one per line)", value=s["highlights"], key=f"eh{i}", height=60)
            )

        st.subheader("Links")
        link_labels: list[str] = []
        link_urls: list[str] = []
        for i in range(MAX_LINK_ROWS):
            ls = link_slots[i] if i < len(link_slots) else {"label": "", "url": ""}
            c1, c2 = st.columns(2)
            with c1:
                link_labels.append(st.text_input(f"Label {i + 1}", value=ls["label"], key=f"ll{i}"))
            with c2:
                link_urls.append(st.text_input(f"URL {i + 1}", value=ls["url"], key=f"lu{i}"))

        st.subheader("Change password (optional)")
        cur_pw = st.text_input("Current password", type="password", autocomplete="current-password")
        new_pw = st.text_input("New password (min 8)", type="password", autocomplete="new-password")

        save = st.form_submit_button("Save profile")

    if not save:
        return

    if not name.strip() or not headline.strip() or not usp.strip():
        st.error("Name, headline, and USP are required.")
        return

    intro_url, verr = parse_optional_video_url(video_url)
    if verr:
        st.error(verr)
        return

    experience: list = []
    for i in range(MAX_EXPERIENCE_ROWS):
        hl = [ln.strip() for ln in exp_highlights[i].splitlines() if ln.strip()]
        t, co, pe = exp_titles[i].strip(), exp_companies[i].strip(), exp_periods[i].strip()
        if not (t or co or pe or hl):
            continue
        experience.append(Experience(title=t, company=co, period=pe, highlights=hl))

    links: dict[str, str] = {}
    for i in range(MAX_LINK_ROWS):
        lab = link_labels[i].strip()
        url = link_urls[i].strip()
        if lab and url:
            links[lab] = url

    usp_lines = [ln.strip() for ln in usp_proof.splitlines() if ln.strip()]
    skill_list = [s.strip() for s in skills.split(",") if s.strip()]
    edu_lines = [ln.strip() for ln in education.splitlines() if ln.strip()]

    new_hash = prof.password_hash
    if new_pw.strip():
        if not prof.password_hash:
            st.error("Cannot set password.")
            return
        if not cur_pw or not verify_password(cur_pw, prof.password_hash):
            st.error("Current password is incorrect.")
            return
        if len(new_pw) < 8:
            st.error("New password must be at least 8 characters.")
            return
        new_hash = hash_password(new_pw)

    photo_url = prof.photo
    if remove_photo:
        delete_uploads_for_username(username)
        photo_url = None

    if up is not None:
        data = up.getvalue()
        if len(data) > MAX_UPLOAD_BYTES:
            st.error("Image must be 2 MB or smaller.")
            return
        ext = guess_image_ext(data)
        if not ext:
            st.error("Invalid image type.")
            return
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        delete_uploads_for_username(username)
        dest = UPLOAD_DIR / f"{username}.{ext}"
        dest.write_bytes(data)
        photo_url = f"/static/uploads/{username}.{ext}"

    updated = JobSeekerProfile(
        name=name.strip(),
        headline=headline.strip(),
        usp=usp.strip(),
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
    st.success("Profile saved.")
    st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="Candidate showcase",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session()

    st.sidebar.title("Navigation")
    if st.session_state.username:
        st.sidebar.caption(f"Signed in as **{st.session_state.username}**")
        if st.sidebar.button("Log out"):
            st.session_state.username = None
            st.rerun()

    options = ["Showcase", "Login", "Register"]
    if st.session_state.username:
        options.append("My profile")

    page = st.sidebar.radio("Page", options, label_visibility="collapsed")

    st.info(
        "**Demo only.** For learning and demonstration. Not for production or sensitive data. "
        "No warranty; use at your own risk."
    )

    if page == "Showcase":
        page_showcase()
    elif page == "Login":
        page_login()
    elif page == "Register":
        if st.session_state.username:
            st.info("You are already logged in. Use **My profile** to edit.")
        else:
            page_register()
    elif page == "My profile":
        page_account()


main()
