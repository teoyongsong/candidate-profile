# Candidate profile showcase

A small Python project for listing job-seeker profiles with a highlighted USP (unique selling proposition), optional employer search, and a web UI where candidates can register, edit their profile, and link a self-introduction video.

**Demo / learning use.** This repository is intended for demonstration and learning. Do not rely on it for production or highly sensitive personal data without a proper security and compliance review.

## Features

- **Showcase (web):** Card layout with uniform card height and scrollable content, optional profile photo, and a button for a self-introduction video URL (Loom, YouTube, Vimeo, etc.).
- **Employer search:** Query parameter `q` filters profiles by keywords across visible fields (AND semantics for multiple words).
- **Candidate accounts:** Register with username and password; bcrypt-hashed passwords; session-based login; edit profile via forms (no raw JSON required for normal edits).
- **Data sources:** JSON under `candidates/` (flat files or `candidates/<username>/profile.json`) plus optional aggregate file via environment variable.
- **CLI:** Terminal showcase with Rich (`showcase.py`), including optional shuffle and JSON merge.

## Requirements

- Python 3.10+ (recommended)
- Dependencies listed in `requirements.txt`

## Installation

```bash
cd candidate-profile
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the web app

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000/` in your browser.

Set a strong random **`SECRET_KEY`** in the environment for any shared or production deployment. The app uses signed cookies for sessions.

## Run the Streamlit app

Same data and bcrypt logic as FastAPI, with a Streamlit UI (sidebar navigation: Showcase, Login, Register, My profile).

```bash
streamlit run streamlit_app.py
```

Opens in your browser (default `http://localhost:8501`).

### Deploy on Streamlit Community Cloud

1. Push this repository to GitHub.
2. In [Streamlit Community Cloud](https://streamlit.io/cloud), create an app: pick the repo, branch, and **Main file path:** `streamlit_app.py`.
3. **Important:** Cloud runtimes use an **ephemeral filesystem**. Files written under `candidates/` or `static/uploads/` during a session **may not persist** across restarts or redeploys. For a real deployment, store profiles in a database or object storage, or treat Cloud only as a **read-only demo** with candidates committed in the repo (no secrets in git).

Optional environment variables (same meaning as above): `CANDIDATES_DIR`, `AGGREGATE_JSON`, `DEMO_MODE`, `NO_SHUFFLE`. You can set secrets in the Cloud app settings if needed.

## Run the terminal showcase

```bash
python showcase.py
python showcase.py --json profile.example.json
python showcase.py --no-shuffle
python showcase.py --demo
```

See `showcase.py --help` for options such as `--candidates-dir`.

## Environment variables (web)

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Signs session cookies (use a long random value in production). |
| `CANDIDATES_DIR` | Override path to the candidates folder (default: `./candidates` next to the app). |
| `AGGREGATE_JSON` | Optional path to a JSON file with a list or `{ "candidates": [ ... ] }` merged with directory-loaded profiles. |
| `DEMO_MODE` | Set to `1` / `true` to use built-in sample profiles only. |
| `NO_SHUFFLE` | Set to `1` / `true` to disable random ordering of cards. |

## Adding candidates

1. **Web:** Use **Register** to create `candidates/<username>/profile.json` with a bcrypt hash (never commit real passwords).
2. **Files:** Add `candidates/your_name.json` (one profile object per file) or `candidates/<username>/profile.json` for account-style layouts.
3. **Bulk:** Use `profile.example.json` as a reference for aggregate JSON if you use `AGGREGATE_JSON`.

Optional fields include `photo` (URL path served under `/static/uploads/…` when uploaded via the app), `self_intro_video_url` (https URL to a video page), `username`, and `password_hash` (bcrypt only if editing by hand).

## API

- `GET /api/candidates` — public candidate data (no passwords). Optional query: `?q=keywords`.
- `GET /?q=keywords` — same filter in the HTML UI.

## Project layout (main files)

| Path | Role |
|------|------|
| `app.py` | FastAPI app: routes, sessions, search, uploads. |
| `streamlit_app.py` | Streamlit UI (showcase, auth, profile edit). |
| `profile.py` | Dataclasses, JSON load/save helpers. |
| `profile_form.py` | Parses structured account form fields. |
| `profile_search.py` | Keyword filter for employers. |
| `auth_password.py` | bcrypt hash and verify. |
| `showcase.py` | CLI Rich renderer and profile collection. |
| `templates/` | Jinja HTML templates. |
| `static/` | CSS and uploaded images (`static/uploads/`). |
| `candidates/` | Profile JSON files. |

## Security notes

- Passwords are stored as **bcrypt hashes**, not plaintext.
- Hashes in JSON on disk are still sensitive: restrict filesystem and backup access.
- Use **HTTPS** in production; set a strong **`SECRET_KEY`**.
- The UI shows a **demo disclaimer** banner; adjust copy in `templates/base.html` if needed.

## License

No license is specified in this repository; add one if you distribute or reuse the code.
