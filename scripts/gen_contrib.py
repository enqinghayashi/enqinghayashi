#!/usr/bin/env python3
"""Draw the contribution calendar as two animated SVGs (dark and light).

The calendar is public, so this reads the same HTML GitHub serves on the
profile page and redraws it on a fixed grid. No token needed.
"""

import datetime as dt
import os
import re
import time
import urllib.request
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "enqinghayashi")
ROOT = Path(__file__).resolve().parent.parent
URL = f"https://github.com/users/{USER}/contributions"

CELL, GAP, RAD = 11, 2, 2.5
PITCH = CELL + GAP
LEFT, TOP = 30, 20

LEVELS = {
    "dark": ["#1b222c", "#0e4429", "#006d32", "#26a641", "#39d353"],
    "light": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
}
TEXT = {"dark": "#7d8590", "light": "#57606a"}
FLASH = {"dark": "#7ee787", "light": "#2da44e"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch() -> dict[str, int]:
    html = ""
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode("utf-8", "replace")
            break
        except Exception as exc:
            if attempt == 2:
                raise SystemExit(f"could not read the contribution page: {exc}")
            time.sleep(5)

    days = {}
    for tag in re.findall(r"<td\b[^>]*>", html):
        date = re.search(r'data-date="(\d{4}-\d{2}-\d{2})"', tag)
        level = re.search(r'data-level="(\d)"', tag)
        if date and level:
            days[date.group(1)] = int(level.group(1))

    if len(days) < 300:
        raise SystemExit(f"only parsed {len(days)} days, the page layout probably changed")
    return days


def build(days: dict[str, int], theme: str) -> str:
    first = dt.date.fromisoformat(min(days))
    last = dt.date.fromisoformat(max(days))
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday
    cols = (last - start).days // 7 + 1

    w = LEFT + cols * PITCH - GAP + 4
    h = TOP + 7 * PITCH - GAP + 4
    fills, text, flash = LEVELS[theme], TEXT[theme], FLASH[theme]

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="Contribution graph for the last 12 months">',
        '<defs><rect id="c" width="11" height="11" rx="2.5"/></defs>',
        f"<style>"
        f".w{{opacity:0;animation:wave 7.5s linear infinite}}"
        f"@keyframes wave{{0%,58%{{opacity:0}}67%{{opacity:.55}}76%{{opacity:0}}100%{{opacity:0}}}}"
        f"@media (prefers-reduced-motion: reduce){{.w{{animation:none}}}}"
        f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
        f"font-size:9px;fill:{text}}}"
        f"</style>",
    ]

    # month labels, skipping the partial month at the start
    y, m = start.year, start.month
    if start.day != 1:
        m += 1
        if m == 13:
            y, m = y + 1, 1
    seen = set()
    while (y, m) <= (last.year, last.month):
        first_of_month = max(dt.date(y, m, 1), start)
        col = (first_of_month - start).days // 7
        if col not in seen:
            seen.add(col)
            out.append(f'<text x="{LEFT + col * PITCH}" y="10">{MONTHS[m - 1]}</text>')
        m += 1
        if m == 13:
            y, m = y + 1, 1

    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="0" y="{TOP + row * PITCH + 9}">{name}</text>')

    for date, level in sorted(days.items()):
        idx = (dt.date.fromisoformat(date) - start).days
        if idx < 0:
            continue
        col, row = idx // 7, idx % 7
        x, y = LEFT + col * PITCH, TOP + row * PITCH
        out.append(f'<use xlink:href="#c" x="{x}" y="{y}" fill="{fills[min(level, 4)]}"/>')
        delay = round(col * 0.09 + row * 0.025, 3)
        out.append(
            f'<use class="w" xlink:href="#c" x="{x}" y="{y}" fill="{flash}" '
            f'style="animation-delay:{delay}s"/>'
        )

    out.append("</svg>")
    return "\n".join(out)


def main() -> None:
    days = fetch()
    for theme in ("dark", "light"):
        path = ROOT / f"contrib-{theme}.svg"
        path.write_text(build(days, theme))
        print(f"{path.name}: {len(days)} days, {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
