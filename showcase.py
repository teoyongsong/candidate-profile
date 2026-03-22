#!/usr/bin/env python3
"""
Render job-seeker profiles as separate terminal cards (USP highlighted per card).

Each person can add ``candidates/<anything>.json`` (one profile object per file).
Order is randomized on each run so no one is always first.

Usage:
  python showcase.py
  python showcase.py --json profile.example.json
  python showcase.py --no-shuffle
  python showcase.py --demo
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from rich import box
from rich.align import Align
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from profile import (
    SAMPLE_CANDIDATES,
    JobSeekerProfile,
    load_profiles_from_directory,
    profiles_from_json_payload,
)

# Rotate styles so adjacent cards are easy to tell apart
_CARD_BORDER_STYLES = (
    "bright_cyan",
    "bright_magenta",
    "bright_green",
    "bright_yellow",
    "bright_blue",
)


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _load_profiles_from_aggregate(path: Path) -> list[JobSeekerProfile]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return profiles_from_json_payload(raw)


def collect_profiles(
    *,
    candidates_dir: Path,
    aggregate_json: Path | None,
    demo_builtin_only: bool,
) -> list[JobSeekerProfile]:
    """Merge per-file candidates, optional aggregate JSON, or built-in demo."""
    if demo_builtin_only:
        return list(SAMPLE_CANDIDATES)

    profiles: list[JobSeekerProfile] = []
    from_dir, dir_errors = load_profiles_from_directory(candidates_dir)
    for msg in dir_errors:
        print(f"Skip: {msg}", file=sys.stderr)
    profiles.extend(from_dir)

    if aggregate_json is not None:
        profiles.extend(_load_profiles_from_aggregate(aggregate_json))

    if not profiles:
        return list(SAMPLE_CANDIDATES)

    return profiles


def _candidate_inner_content(p: JobSeekerProfile) -> Group:
    """Body of one candidate card (USP first, then rest)."""
    usp_md = f"**{p.usp}**"
    for line in p.usp_proof_points:
        usp_md += f"\n- {line}"
    usp_panel = Panel(
        Markdown(usp_md.strip()),
        title="[bold]Unique value[/bold]",
        subtitle="[dim]USP & proof[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    parts: list[RenderableType] = [usp_panel]

    if p.skills:
        parts.append(Rule("[bold]Skills[/bold]", style="dim"))
        skill_row = " · ".join(f"[green]{s}[/green]" for s in p.skills)
        parts.append(Align.center(Text.from_markup(skill_row)))
        parts.append(Text(""))

    if p.experience:
        parts.append(Rule("[bold]Experience[/bold]", style="dim"))
        for job in p.experience:
            header = (
                f"[bold]{job.title}[/bold] — {job.company}  [dim]{job.period}[/dim]"
            )
            parts.append(Text.from_markup(header))
            for h in job.highlights:
                parts.append(Text(f"  • {h}"))
            parts.append(Text(""))

    if p.education:
        parts.append(Rule("[bold]Education[/bold]", style="dim"))
        for line in p.education:
            parts.append(Text(f"  {line}"))
        parts.append(Text(""))

    if p.links:
        parts.append(Rule("[bold]Links[/bold]", style="dim"))
        t = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        t.add_column("Label", style="cyan")
        t.add_column("URL")
        for label, url in p.links.items():
            t.add_row(label, url)
        parts.append(t)

    for section, lines in (p.extras or {}).items():
        parts.append(Rule(f"[bold]{section}[/bold]", style="dim"))
        for line in lines:
            parts.append(Text(f"  • {line}"))
        parts.append(Text(""))

    return Group(*parts)


def _candidate_card(p: JobSeekerProfile, index: int) -> Panel:
    """One outer card per candidate."""
    border = _CARD_BORDER_STYLES[index % len(_CARD_BORDER_STYLES)]
    subtitle = Text(p.headline, style="italic dim")
    return Panel(
        _candidate_inner_content(p),
        title=f"[bold white]{p.name}[/bold white]",
        title_align="left",
        subtitle=subtitle,
        subtitle_align="left",
        border_style=border,
        box=box.HEAVY,
        padding=(1, 2),
    )


def render_candidates(
    profiles: list[JobSeekerProfile],
    console: Console,
    *,
    order_note: str | None = None,
) -> None:
    if not profiles:
        console.print("[yellow]No candidates to display.[/yellow]")
        return

    lines = (
        "[bold]Candidate showcase[/bold]\n"
        "[dim]One card per person · USP inside each card[/dim]"
    )
    if order_note:
        lines += f"\n[dim]{order_note}[/dim]"
    console.print(Align.center(Text.from_markup(lines)))
    console.print()

    for i, profile in enumerate(profiles):
        console.print(_candidate_card(profile, i))
        if i < len(profiles) - 1:
            console.print()


def main() -> int:
    default_dir = _script_dir() / "candidates"

    parser = argparse.ArgumentParser(
        description=(
            "Showcase job-seeker profiles as separate cards. "
            "Add candidates/your-name.json (one profile per file). "
            "Card order is randomized each run unless --no-shuffle."
        ),
    )
    parser.add_argument(
        "--candidates-dir",
        type=Path,
        default=default_dir,
        metavar="DIR",
        help=f"Directory of one JSON file per candidate (default: {default_dir})",
    )
    parser.add_argument(
        "--json",
        type=Path,
        metavar="FILE",
        help="Optional aggregate JSON (list or {{candidates: [...]}}) merged after directory files",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Use built-in sample profiles only (ignore candidates/ and --json)",
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Keep load order (directory files sorted by name, then --json)",
    )
    args = parser.parse_args()

    if args.json and not args.demo and not args.json.is_file():
        print(f"File not found: {args.json}", file=sys.stderr)
        return 1

    profiles = collect_profiles(
        candidates_dir=args.candidates_dir.resolve(),
        aggregate_json=args.json,
        demo_builtin_only=args.demo,
    )

    if not args.no_shuffle and len(profiles) > 1:
        random.shuffle(profiles)

    order_note = None
    if not args.no_shuffle and len(profiles) > 1:
        order_note = "Order randomized each run — equal visibility for every candidate"

    console = Console()
    render_candidates(profiles, console, order_note=order_note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
