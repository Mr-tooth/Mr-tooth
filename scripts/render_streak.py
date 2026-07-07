#!/usr/bin/env python3
import argparse
import html
import json
import os
import sys
import urllib.request


QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_calendar(login, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Mr-tooth-profile-stats",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days):
    days = sorted(days, key=lambda day: day["date"])
    longest = current = run = 0
    for day in days:
        if day["contributionCount"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    for day in reversed(days):
        if day["contributionCount"] <= 0:
            break
        current += 1
    return current, longest, days[-1]["date"]


def render_svg(login, total, current, longest, updated):
    title = html.escape(f"{login} contribution streak")
    return f"""<svg width="467" height="195" viewBox="0 0 467 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">
  <title id="title">{title}</title>
  <desc id="desc">Current streak: {current} days. Longest streak: {longest} days. Total contributions this year: {total}.</desc>
  <style>
    .header {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #006AFF; }}
    .label {{ font: 400 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #417E87; }}
    .value {{ font: 700 28px 'Segoe UI', Ubuntu, Sans-Serif; fill: #417E87; }}
    .small {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #417E87; opacity: .75; }}
    .ring {{ stroke: #006AFF; fill: none; stroke-width: 7; opacity: .18; }}
    .arc {{ stroke: #006AFF; fill: none; stroke-width: 7; stroke-linecap: round; opacity: .85; }}
  </style>
  <rect width="467" height="195" rx="4" fill="transparent"/>
  <text class="header" x="30" y="34">Contribution Streak</text>
  <circle class="ring" cx="94" cy="102" r="46"/>
  <circle class="arc" cx="94" cy="102" r="46" pathLength="100" stroke-dasharray="{min(current, 100)} 100" transform="rotate(-90 94 102)"/>
  <text class="value" x="94" y="96" text-anchor="middle">{current}</text>
  <text class="label" x="94" y="118" text-anchor="middle">days</text>
  <text class="label" x="180" y="82">Longest streak</text>
  <text class="value" x="180" y="113">{longest} days</text>
  <text class="label" x="180" y="143">Year contributions</text>
  <text class="value" x="315" y="143">{total}</text>
  <text class="small" x="30" y="174">Updated from GitHub GraphQL on {updated}</text>
</svg>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--user")
    parser.add_argument("--output")
    args = parser.parse_args()
    if args.self_test:
        sample = [
            {"date": "2026-01-01", "contributionCount": 1},
            {"date": "2026-01-02", "contributionCount": 1},
            {"date": "2026-01-03", "contributionCount": 0},
            {"date": "2026-01-04", "contributionCount": 2},
            {"date": "2026-01-05", "contributionCount": 3},
            {"date": "2026-01-06", "contributionCount": 4},
        ]
        assert streaks(sample) == (3, 3, "2026-01-06")
        assert "Current streak: 3 days" in render_svg("tester", 11, 3, 3, "2026-01-06")
        return
    if not args.user or not args.output:
        parser.error("--user and --output are required unless --self-test is set")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN or GH_TOKEN is required")
    calendar = fetch_calendar(args.user, token)
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    current, longest, updated = streaks(days)
    svg = render_svg(args.user, calendar["totalContributions"], current, longest, updated)
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as file:
        file.write(svg)


if __name__ == "__main__":
    main()
