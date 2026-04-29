#!/usr/bin/env python3
import os
import sys
import requests
from datetime import datetime, timezone, timedelta

TOKEN    = os.environ.get("METRICS_TOKEN", "")
USERNAME = "IanVDev"
OUT      = os.path.join(os.environ.get("GITHUB_WORKSPACE", "."), "ianvdev-os.svg")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount }
        }
      }
    }
    repositories(
      first: 100
      ownerAffiliations: [OWNER]
      isFork: false
      orderBy: { field: UPDATED_AT, direction: DESC }
    ) {
      nodes {
        stargazerCount
        languages(first: 6, orderBy: { field: SIZE, direction: DESC }) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""

def gql(query, variables):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"bearer {TOKEN}"},
        timeout=20,
    )
    r.raise_for_status()
    body = r.json()
    if "errors" in body:
        print(f"GraphQL errors: {body['errors']}", file=sys.stderr)
        sys.exit(1)
    return body["data"]


def streak_from_calendar(weeks, today):
    days = sorted(
        [d for w in weeks for d in w["contributionDays"]],
        key=lambda d: d["date"],
    )
    count = 0
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["contributionCount"] > 0:
            count += 1
        elif d["date"] == today:
            continue
        else:
            break
    return count


def top_languages(repos, limit=5):
    lang_map = {}
    for repo in repos:
        for edge in repo["languages"]["edges"]:
            n = edge["node"]["name"]
            c = edge["node"]["color"] or "#8b949e"
            s = edge["size"]
            if n not in lang_map:
                lang_map[n] = {"size": 0, "color": c}
            lang_map[n]["size"] += s
    total = sum(v["size"] for v in lang_map.values()) or 1
    ranked = sorted(lang_map.items(), key=lambda x: x[1]["size"], reverse=True)
    return ranked[:limit], total


def fmt(n):
    return f"{n:,}" if n >= 1_000 else str(n)


def build_svg(total, commits, prs, reviews, streak, stars, langs, total_size, year):
    W, H = 580, 320

    lang_rows_svg = ""
    for i, (name, info) in enumerate(langs):
        pct = info["size"] / total_size * 100
        bar_w = max(2, int(pct / 100 * 190))
        color = info["color"] or "#8b949e"
        y = 200 + i * 20
        lang_rows_svg += f"""
    <text x="44" y="{y}" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">{name}</text>
    <rect x="140" y="{y - 10}" width="{bar_w}" height="7" rx="2" fill="{color}" opacity="0.9"/>
    <text x="348" y="{y}" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">{pct:.1f}%</text>"""

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return f"""<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="{W}" y2="{H}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#0d1117"/>
      <stop offset="100%" stop-color="#161b22"/>
    </linearGradient>
  </defs>

  <rect width="{W}" height="{H}" rx="12" fill="url(#bg)" stroke="#30363d" stroke-width="1"/>

  <!-- Title bar -->
  <rect width="{W}" height="36" rx="12" fill="#161b22"/>
  <rect y="24" width="{W}" height="12" fill="#161b22"/>
  <circle cx="20" cy="18" r="5" fill="#ff5f56"/>
  <circle cx="36" cy="18" r="5" fill="#ffbd2e"/>
  <circle cx="52" cy="18" r="5" fill="#27c93f"/>
  <text x="{W // 2}" y="22" text-anchor="middle" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">IanVDev OS — github.com/IanVDev</text>

  <!-- Activity -->
  <text x="28" y="60" fill="#58a6ff" font-size="11" font-family="'Courier New',monospace" font-weight="bold">▸ ACTIVITY  ({year})</text>
  <line x1="28" y1="66" x2="{W - 28}" y2="66" stroke="#21262d" stroke-width="1"/>

  <text x="44"  y="84" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Contributions</text>
  <text x="200" y="84" fill="#e6edf3" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{fmt(total)}</text>

  <text x="44"  y="102" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Commits</text>
  <text x="200" y="102" fill="#e6edf3" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{fmt(commits)}</text>

  <text x="44"  y="120" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Pull Requests</text>
  <text x="200" y="120" fill="#e6edf3" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{fmt(prs)}</text>

  <text x="44"  y="138" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Code Reviews</text>
  <text x="200" y="138" fill="#e6edf3" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{fmt(reviews)}</text>

  <!-- Right column -->
  <text x="360" y="84"  fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Current Streak</text>
  <text x="500" y="84"  fill="#f0883e" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{streak}d</text>

  <text x="360" y="102" fill="#8b949e" font-size="11" font-family="'Courier New',monospace">Stars Earned</text>
  <text x="500" y="102" fill="#e3b341" font-size="11" font-family="'Courier New',monospace" font-weight="bold">{fmt(stars)}</text>

  <!-- Languages -->
  <text x="28" y="172" fill="#58a6ff" font-size="11" font-family="'Courier New',monospace" font-weight="bold">▸ LANGUAGES</text>
  <line x1="28" y1="178" x2="{W - 28}" y2="178" stroke="#21262d" stroke-width="1"/>

  {lang_rows_svg}

  <!-- Footer -->
  <line x1="28" y1="{H - 22}" x2="{W - 28}" y2="{H - 22}" stroke="#21262d" stroke-width="1"/>
  <text x="28" y="{H - 9}" fill="#30363d" font-size="10" font-family="'Courier New',monospace">updated {today_str}</text>
  <text x="{W - 28}" y="{H - 9}" text-anchor="end" fill="#30363d" font-size="10" font-family="'Courier New',monospace">fail-closed · reliability first</text>
</svg>"""


def main():
    now        = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    today      = now.strftime("%Y-%m-%d")

    data   = gql(QUERY, {"login": USERNAME, "from": year_start.isoformat(), "to": now.isoformat()})
    user   = data["user"]
    cc     = user["contributionsCollection"]
    repos  = user["repositories"]["nodes"]

    total   = cc["contributionCalendar"]["totalContributions"]
    commits = cc["totalCommitContributions"]
    prs     = cc["totalPullRequestContributions"]
    reviews = cc["totalPullRequestReviewContributions"]
    streak  = streak_from_calendar(cc["contributionCalendar"]["weeks"], today)
    stars   = sum(r["stargazerCount"] for r in repos)

    langs, total_size = top_languages(repos)

    svg = build_svg(total, commits, prs, reviews, streak, stars, langs, total_size, now.year)

    with open(OUT, "w") as f:
        f.write(svg)
    print(f"Written: {OUT}")


if __name__ == "__main__":
    main()
