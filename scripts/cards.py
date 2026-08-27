#!/usr/bin/env python3
"""
cards.py — draws project cards in a "benchmark report" style: repo name,
one-line result, live stars/language pulled from the GitHub API, laid out
like a lab report row rather than a generic stat badge.

Usage:
    python cards.py --user omni-ar --projects assets/projects.json --out assets

Requires: requests
"""
import argparse
import json
import os
from xml.sax.saxutils import escape as xml_escape

DARK_BG = "#0D1117"
LIGHT_BG = "#FFFFFF"
ACCENT = "#00D9FF"
DARK_TEXT = "#C9D1D9"
LIGHT_TEXT = "#24292F"
DARK_BORDER = "#30363D"
LIGHT_BORDER = "#D0D7DE"
DARK_MUTED = "#8B949E"
LIGHT_MUTED = "#57606A"


def fetch_repo(user, repo, token=None):
    import requests
    headers = {"Accept": "application/vnd.github+json", "User-Agent": f"{user}-profile-cards"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"https://api.github.com/repos/{user}/{repo}", headers=headers, timeout=15)
    if resp.status_code != 200:
        return {"stars": None, "language": None, "forks": None}
    data = resp.json()
    return {
        "stars": data.get("stargazers_count"),
        "language": data.get("language"),
        "forks": data.get("forks_count"),
    }


def card_svg(project, theme="dark"):
    bg = DARK_BG if theme == "dark" else LIGHT_BG
    text = DARK_TEXT if theme == "dark" else LIGHT_TEXT
    border = DARK_BORDER if theme == "dark" else LIGHT_BORDER
    muted = DARK_MUTED if theme == "dark" else LIGHT_MUTED

    W, H = 440, 150
    name = xml_escape(project["repo"])
    result = xml_escape(project.get("result", ""))
    desc = xml_escape(project.get("description", ""))
    stack = xml_escape(" · ".join(project.get("stack", [])))
    stars = project.get("stars")
    language = project.get("language")

    meta_bits = []
    if language:
        meta_bits.append(xml_escape(language))
    if stars is not None:
        meta_bits.append(f"\u2605 {stars}")
    meta = "   ".join(meta_bits)

    parts = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">',
        f'<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="8" fill="{bg}" stroke="{border}" stroke-width="1"/>',
        f'<text x="20" y="30" fill="{text}" font-size="15" font-weight="600">{name}</text>',
        f'<text x="{W-20}" y="30" fill="{muted}" font-size="10" text-anchor="end">{meta}</text>',
        f'<line x1="20" y1="42" x2="{W-20}" y2="42" stroke="{border}" stroke-width="1"/>',
        f'<text x="20" y="62" fill="{ACCENT}" font-size="11" letter-spacing="1">RESULT \u2192</text>',
        f'<text x="20" y="80" fill="{text}" font-size="12">{result}</text>',
        f'<text x="20" y="104" fill="{muted}" font-size="10" letter-spacing="1">METHOD \u2192</text>',
        f'<text x="20" y="120" fill="{text}" font-size="11">{desc}</text>',
        f'<text x="20" y="138" fill="{muted}" font-size="9">{stack}</text>',
        "</svg>",
    ]
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--user", required=True)
    ap.add_argument("--projects", required=True)
    ap.add_argument("--out", default="assets")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    ap.add_argument("--offline", action="store_true", help="skip GitHub API calls, use projects.json values only")
    args = ap.parse_args()

    with open(args.projects) as f:
        cfg = json.load(f)

    for project in cfg["projects"]:
        if not args.offline:
            live = fetch_repo(args.user, project["repo"], args.token or None)
            project.update({k: v for k, v in live.items() if v is not None})
        for theme in ("dark", "light"):
            svg = card_svg(project, theme=theme)
            path = f'{args.out}/card-{project["repo"].lower()}-{theme}.svg'
            with open(path, "w") as f:
                f.write(svg)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
