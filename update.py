"""Rebuild README.md from my pull requests on GitHub.

Lists merged PRs (grouped by project, with star counts) and PRs still under review.
Runs weekly from GitHub Actions; can also be run locally with GITHUB_TOKEN set.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

USER = "kratos0718"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json",
                                               **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def search_prs(state: str) -> list[dict]:
    q = urllib.parse.quote(f"is:pr author:{USER} {state} -user:{USER}")
    items, page = [], 1
    while True:
        data = get(f"{API}/search/issues?q={q}&per_page=100&page={page}&sort=updated")
        items += data["items"]
        if len(items) >= data["total_count"] or not data["items"]:
            return items
        page += 1


_stars: dict[str, int] = {}


def stars(repo: str) -> int:
    if repo not in _stars:
        _stars[repo] = get(f"{API}/repos/{repo}")["stargazers_count"]
    return _stars[repo]


def fmt_stars(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def repo_of(item: dict) -> str:
    return item["repository_url"].removeprefix(f"{API}/repos/")


def main() -> None:
    merged = search_prs("is:merged")
    open_prs = search_prs("is:open")

    by_repo: dict[str, list[dict]] = defaultdict(list)
    for pr in merged:
        by_repo[repo_of(pr)].append(pr)
    orgs = {r.split("/")[0] for r in by_repo}
    total_stars = sum(stars(r) for r in by_repo)

    lines = [
        "# Open-source contributions",
        "",
        f"Pull requests I've had merged into other people's projects, reviewed and merged by their maintainers.",
        "",
        f"**{len(merged)} merged PRs** across **{len(orgs)} organizations** and **{len(by_repo)} repositories** "
        f"with **{fmt_stars(total_stars)}** combined GitHub stars.",
        "",
        "## Merged",
        "",
        "| Project | Stars | Pull request | Merged |",
        "|---|---|---|---|",
    ]
    for repo in sorted(by_repo, key=lambda r: (-stars(r), r)):
        for pr in sorted(by_repo[repo], key=lambda p: p["closed_at"], reverse=True):
            lines.append(f"| [{repo}](https://github.com/{repo}) | {fmt_stars(stars(repo))} | "
                         f"[#{pr['number']} {pr['title'].replace('|', '/')}]({pr['html_url']}) | "
                         f"{pr['closed_at'][:10]} |")

    lines += ["", "## Under review", "", "| Project | Pull request | Opened |", "|---|---|---|"]
    for pr in sorted(open_prs, key=lambda p: p["created_at"], reverse=True):
        repo = repo_of(pr)
        lines.append(f"| [{repo}](https://github.com/{repo}) | "
                     f"[#{pr['number']} {pr['title'].replace('|', '/')}]({pr['html_url']}) | "
                     f"{pr['created_at'][:10]} |")

    lines += ["", f"<sub>Updated {datetime.now(timezone.utc):%Y-%m-%d} from the GitHub API by `update.py`.</sub>", ""]
    with open("README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"{len(merged)} merged, {len(orgs)} orgs, {len(open_prs)} open")


if __name__ == "__main__":
    main()
