#!/usr/bin/env python3
"""
radar.py — draws a "benchmark results" radar chart: either your own
self-rated values (--data) or real language-byte counts pulled live
from the GitHub API (--github).

Usage:
    python radar.py --data assets/skills.json -o assets/radar
    python radar.py --github omni-ar -o assets/radar-langs --limit 7 --curve 0.4 \
        --exclude "html,css,shell,dockerfile"

Requires: requests (only for --github mode)
"""
import argparse
import json
import math
import os
from xml.sax.saxutils import escape as xml_escape

DARK_BG = "#0D1117"
LIGHT_BG = "#FFFFFF"
ACCENT = "#00D9FF"
DARK_TEXT = "#C9D1D9"
LIGHT_TEXT = "#24292F"
DARK_GRID = "#30363D"
LIGHT_GRID = "#D0D7DE"


def fetch_language_bytes(username, exclude=None, token=None):
    import requests
    exclude = {e.strip().lower() for e in (exclude or "").split(",") if e.strip()}
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{username}-profile-radar"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    totals = {}
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 100, "page": page, "type": "owner"},
            headers=headers, timeout=15,
        )
        resp.raise_for_status()
        repos = resp.json()
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            langs_resp = requests.get(repo["languages_url"], headers=headers, timeout=15)
            if langs_resp.status_code != 200:
                continue
            for lang, count in langs_resp.json().items():
                if lang.lower() in exclude:
                    continue
                totals[lang] = totals.get(lang, 0) + count
        page += 1
    return totals


def curve_values(values, curve):
    """1.0 = linear, lower = compress lopsided byte counts (log-ish scale)."""
    if not values:
        return values
    m = max(values) or 1
    return [(v / m) ** curve for v in values]


def polygon_points(cx, cy, radius, n, rotate=-90):
    pts = []
    for i in range(n):
        angle = math.radians(rotate + i * 360 / n)
        pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return pts


def build_radar_svg(labels, raw_values, scaled_fracs, theme="dark", title="BENCHMARK: SELF-RATED",
                     show_values=True, unit=""):
    bg = DARK_BG if theme == "dark" else LIGHT_BG
    text = DARK_TEXT if theme == "dark" else LIGHT_TEXT
    grid = DARK_GRID if theme == "dark" else LIGHT_GRID

    W, H = 560, 460
    cx, cy = W / 2, H / 2 + 14
    R = 130
    n = len(labels)

    parts = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">',
        f'<rect width="{W}" height="{H}" fill="{bg}"/>',
        f'<text x="{W/2}" y="24" fill="{text}" font-size="12" letter-spacing="2" text-anchor="middle" opacity="0.75">{xml_escape(title)}</text>',
    ]

    # grid rings
    for ring in (0.25, 0.5, 0.75, 1.0):
        pts = polygon_points(cx, cy, R * ring, n)
        pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(f'<polygon points="{pts_str}" fill="none" stroke="{grid}" stroke-width="1"/>')

    # spokes
    for (x, y) in polygon_points(cx, cy, R, n):
        parts.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{grid}" stroke-width="1"/>')

    # data polygon
    data_pts = polygon_points(cx, cy, R, n)
    scaled_pts = [
        (cx + (x - cx) * f, cy + (y - cy) * f)
        for (x, y), f in zip(data_pts, scaled_fracs)
    ]
    pts_str = " ".join(f"{x:.1f},{y:.1f}" for x, y in scaled_pts)
    parts.append(f'<polygon points="{pts_str}" fill="{ACCENT}" fill-opacity="0.22" stroke="{ACCENT}" stroke-width="2"/>')
    for x, y in scaled_pts:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{ACCENT}"/>')

    # labels + values
    label_pts = polygon_points(cx, cy, R + 34, n)
    for (x, y), label, raw in zip(label_pts, labels, raw_values):
        anchor = "middle"
        if x < cx - 10:
            anchor = "end"
        elif x > cx + 10:
            anchor = "start"
        val_str = xml_escape(f"{raw}{unit}") if show_values else ""
        parts.append(f'<text x="{x:.1f}" y="{y:.1f}" fill="{text}" font-size="11" text-anchor="{anchor}">{xml_escape(str(label))}</text>')
        if show_values:
            parts.append(f'<text x="{x:.1f}" y="{y+13:.1f}" fill="{ACCENT}" font-size="10" text-anchor="{anchor}" opacity="0.85">{val_str}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", help="path to skills JSON (self-rated)")
    ap.add_argument("--github", help="GitHub username to pull language bytes from")
    ap.add_argument("-o", "--out", required=True, help="output path prefix (writes -dark.svg / -light.svg)")
    ap.add_argument("--limit", type=int, default=7)
    ap.add_argument("--curve", type=float, default=0.4)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    args = ap.parse_args()

    if args.data:
        with open(args.data) as f:
            cfg = json.load(f)
        labels = [a["label"] for a in cfg["axes"]][: args.limit]
        raw = [a["value"] for a in cfg["axes"]][: args.limit]
        title = cfg.get("title", "BENCHMARK: SELF-RATED").upper()
        fracs = [v / 100 for v in raw]
        unit = ""
    elif args.github:
        totals = fetch_language_bytes(args.github, args.exclude, args.token or None)
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[: args.limit]
        labels = [k for k, _ in ranked]
        raw_bytes = [v for _, v in ranked]
        fracs = curve_values(raw_bytes, args.curve)
        title = "BENCHMARK: VERIFIED FROM COMMITS"
        # show as KB for readability
        raw = [f"{v/1024:.0f}KB" for v in raw_bytes]
        unit = ""
    else:
        raise SystemExit("pass --data or --github")

    for theme in ("dark", "light"):
        svg = build_radar_svg(labels, raw, fracs, theme=theme, title=title, unit=unit)
        path = f"{args.out}-{theme}.svg"
        with open(path, "w") as f:
            f.write(svg)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
