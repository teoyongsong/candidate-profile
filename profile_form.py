"""Parse profile edit forms (structured fields, no raw JSON)."""

from __future__ import annotations

from typing import Any

from profile import Experience


MAX_EXPERIENCE_ROWS = 8
MAX_LINK_ROWS = 10


def experience_from_form(form: Any) -> list[Experience]:
    """Build experience list from exp_{i}_* fields."""
    out: list[Experience] = []
    for i in range(MAX_EXPERIENCE_ROWS):
        title = (form.get(f"exp_{i}_title") or "").strip()
        company = (form.get(f"exp_{i}_company") or "").strip()
        period = (form.get(f"exp_{i}_period") or "").strip()
        highlights_raw = (form.get(f"exp_{i}_highlights") or "").strip()
        highlights = [ln.strip() for ln in highlights_raw.splitlines() if ln.strip()]
        if not (title or company or period or highlights):
            continue
        out.append(
            Experience(
                title=title,
                company=company,
                period=period,
                highlights=highlights,
            )
        )
    return out


def links_from_form(form: Any) -> dict[str, str]:
    """Build links dict from link_{i}_label / link_{i}_url."""
    out: dict[str, str] = {}
    for i in range(MAX_LINK_ROWS):
        label = (form.get(f"link_{i}_label") or "").strip()
        url = (form.get(f"link_{i}_url") or "").strip()
        if label and url:
            out[label] = url
    return out


def experience_slots_for_template(profile_experience: list[Experience]) -> list[dict[str, str]]:
    """Prefill rows for the HTML form (padded to MAX_EXPERIENCE_ROWS)."""
    slots: list[dict[str, str]] = []
    for j in profile_experience:
        slots.append(
            {
                "title": j.title,
                "company": j.company,
                "period": j.period,
                "highlights": "\n".join(j.highlights),
            }
        )
    while len(slots) < MAX_EXPERIENCE_ROWS:
        slots.append({"title": "", "company": "", "period": "", "highlights": ""})
    return slots[:MAX_EXPERIENCE_ROWS]


def link_slots_for_template(links: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label, url in links.items():
        rows.append({"label": label, "url": url})
    while len(rows) < MAX_LINK_ROWS:
        rows.append({"label": "", "url": ""})
    return rows[:MAX_LINK_ROWS]


def experience_slots_from_form(form: Any) -> list[dict[str, str]]:
    """Rebuild slot dicts after a failed save (for re-rendering the form)."""
    slots: list[dict[str, str]] = []
    for i in range(MAX_EXPERIENCE_ROWS):
        slots.append(
            {
                "title": (form.get(f"exp_{i}_title") or "").strip(),
                "company": (form.get(f"exp_{i}_company") or "").strip(),
                "period": (form.get(f"exp_{i}_period") or "").strip(),
                "highlights": (form.get(f"exp_{i}_highlights") or "").strip(),
            }
        )
    return slots


def link_slots_from_form(form: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for i in range(MAX_LINK_ROWS):
        rows.append(
            {
                "label": (form.get(f"link_{i}_label") or "").strip(),
                "url": (form.get(f"link_{i}_url") or "").strip(),
            }
        )
    return rows
