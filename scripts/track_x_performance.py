#!/usr/bin/env python3
"""Fetch recent X posts for a username, save raw/structured data, and render a short report.

MVP scope:
- Uses X API v2 with bearer token from X_API_BEARER_TOKEN env var
- Fetches user profile + recent tweets for a username
- Stores raw API responses and normalized snapshots under memory/x-metrics/
- Writes a markdown summary report and appends a short entry to memory/performance-log.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.twitter.com/2"
DEFAULT_USERNAME = "RiccSartori"
DEFAULT_LIMIT = 10
ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
DATA_DIR = MEMORY_DIR / "x-metrics"


@dataclass
class TweetSnapshot:
    id: str
    created_at: str
    text: str
    url: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    bookmark_count: int | None
    impression_count: int | None
    engagement_total: int
    media_keys: list[str]
    is_reply: bool


def require_bearer_token() -> str:
    token = os.environ.get("X_API_BEARER_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Missing X_API_BEARER_TOKEN in environment. Set it before running this script."
        )
    return token


def build_ssl_context() -> ssl.SSLContext:
    cafile = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if cafile:
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()



def x_get(path: str, params: dict[str, Any], bearer_token: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "pulse-x-performance-tracker/0.1",
        },
    )
    ssl_context = build_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"X API error {exc.code}: {body[:800]}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error while calling X API: {exc}") from exc



def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)



def fetch_user(username: str, bearer_token: str) -> dict[str, Any]:
    return x_get(
        f"/users/by/username/{username}",
        {
            "user.fields": "public_metrics,description,created_at,verified,profile_image_url",
        },
        bearer_token,
    )



def fetch_tweets(user_id: str, limit: int, bearer_token: str) -> dict[str, Any]:
    capped_limit = max(5, min(limit, 100))
    return x_get(
        f"/users/{user_id}/tweets",
        {
            "max_results": capped_limit,
            "exclude": "retweets",
            "tweet.fields": "created_at,public_metrics,entities,conversation_id,referenced_tweets",
            "expansions": "attachments.media_keys",
            "media.fields": "type,url,preview_image_url",
        },
        bearer_token,
    )



def normalize_tweets(username: str, tweets_payload: dict[str, Any]) -> list[TweetSnapshot]:
    snapshots: list[TweetSnapshot] = []
    for item in tweets_payload.get("data", []):
        metrics = item.get("public_metrics", {})
        media_keys = item.get("attachments", {}).get("media_keys", [])
        refs = item.get("referenced_tweets", []) or []
        is_reply = any(ref.get("type") == "replied_to" for ref in refs)
        tweet_id = item["id"]
        snapshots.append(
            TweetSnapshot(
                id=tweet_id,
                created_at=item.get("created_at", ""),
                text=item.get("text", "").replace("\r", " ").strip(),
                url=f"https://x.com/{username}/status/{tweet_id}",
                like_count=metrics.get("like_count", 0),
                retweet_count=metrics.get("retweet_count", 0),
                reply_count=metrics.get("reply_count", 0),
                quote_count=metrics.get("quote_count", 0),
                bookmark_count=metrics.get("bookmark_count"),
                impression_count=metrics.get("impression_count"),
                engagement_total=(
                    metrics.get("like_count", 0)
                    + metrics.get("retweet_count", 0)
                    + metrics.get("reply_count", 0)
                    + metrics.get("quote_count", 0)
                ),
                media_keys=media_keys,
                is_reply=is_reply,
            )
        )
    return snapshots



def build_summary(username: str, user_payload: dict[str, Any], tweets: list[TweetSnapshot], fetched_at: str) -> str:
    user = user_payload.get("data", {})
    metrics = user.get("public_metrics", {})
    followers = metrics.get("followers_count", 0)
    tweet_count = metrics.get("tweet_count", 0)

    if tweets:
        avg_engagement = round(sum(t.engagement_total for t in tweets) / len(tweets), 2)
        top_by_engagement = max(tweets, key=lambda t: t.engagement_total)
        top_by_likes = max(tweets, key=lambda t: t.like_count)
        total_impressions = sum(t.impression_count or 0 for t in tweets)
    else:
        avg_engagement = 0
        top_by_engagement = None
        top_by_likes = None
        total_impressions = 0

    lines = [
        f"# X Performance Summary for @{username}",
        "",
        f"Fetched at: {fetched_at}",
        f"Followers: {followers}",
        f"Total tweets on account: {tweet_count}",
        f"Posts analyzed: {len(tweets)}",
        f"Average engagement per post: {avg_engagement}",
        f"Total impressions across analyzed posts: {total_impressions}",
        "",
    ]

    if top_by_engagement:
        lines.extend(
            [
                "## Best post by engagement",
                f"- URL: {top_by_engagement.url}",
                f"- Published: {top_by_engagement.created_at}",
                f"- Engagement: {top_by_engagement.engagement_total}",
                f"- Metrics: {top_by_engagement.like_count} likes, {top_by_engagement.retweet_count} reposts, {top_by_engagement.reply_count} replies, {top_by_engagement.quote_count} quotes",
                f"- Text: {top_by_engagement.text[:240]}",
                "",
            ]
        )

    if top_by_likes and top_by_likes.id != getattr(top_by_engagement, "id", None):
        lines.extend(
            [
                "## Best post by likes",
                f"- URL: {top_by_likes.url}",
                f"- Published: {top_by_likes.created_at}",
                f"- Likes: {top_by_likes.like_count}",
                f"- Text: {top_by_likes.text[:240]}",
                "",
            ]
        )

    lines.append("## Recent posts")
    if not tweets:
        lines.append("- No posts returned by the API.")
    else:
        for tweet in tweets:
            lines.extend(
                [
                    f"### {tweet.created_at} · {tweet.engagement_total} engagements",
                    f"- URL: {tweet.url}",
                    f"- Metrics: {tweet.like_count} likes, {tweet.retweet_count} reposts, {tweet.reply_count} replies, {tweet.quote_count} quotes, {tweet.bookmark_count or 0} bookmarks, {tweet.impression_count or 0} impressions",
                    f"- Reply: {'yes' if tweet.is_reply else 'no'} | Media attached: {'yes' if tweet.media_keys else 'no'}",
                    f"- Text: {tweet.text[:280]}",
                    "",
                ]
            )

    return "\n".join(lines).strip() + "\n"



def append_performance_log(username: str, user_payload: dict[str, Any], tweets: list[TweetSnapshot], fetched_at: str) -> None:
    path = MEMORY_DIR / "performance-log.md"
    user = user_payload.get("data", {})
    followers = user.get("public_metrics", {}).get("followers_count", 0)

    sorted_tweets = sorted(tweets, key=lambda t: t.engagement_total, reverse=True)

    lines = [f"## Auto snapshot for @{username} - logged {fetched_at}"]
    lines.append(f"- Followers at snapshot: {followers}")
    lines.append(f"- Posts analyzed: {len(tweets)}")
    lines.append("")

    if sorted_tweets:
        lines.append("### All analyzed posts (sorted by engagement)")
        lines.append("| URL | Likes | Reposts | Replies | Quotes | Bookmarks | Impressions | Total engagement |")
        lines.append("|-----|-------|---------|---------|--------|-----------|-------------|-----------------|")
        for t in sorted_tweets:
            lines.append(
                f"| {t.url} | {t.like_count} | {t.retweet_count} | {t.reply_count} | {t.quote_count} | {t.bookmark_count or 0} | {t.impression_count or 0} | {t.engagement_total} |"
            )
        lines.append("")
        lines.append("### Post details")
        for t in sorted_tweets:
            lines.append(f"**{t.url}** ({t.created_at})")
            lines.append(f"- Text: {t.text[:200]}")
            lines.append(f"- Reply: {'yes' if t.is_reply else 'no'} | Media: {'yes' if t.media_keys else 'no'}")
            lines.append("")

    lines.append("")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")



def save_outputs(username: str, user_payload: dict[str, Any], tweets_payload: dict[str, Any], tweets: list[TweetSnapshot], summary: str, fetched_at: str) -> dict[str, Path]:
    stamp = fetched_at.replace(":", "-")
    raw_path = DATA_DIR / f"{username}-raw-{stamp}.json"
    structured_path = DATA_DIR / f"{username}-snapshot-{stamp}.json"
    report_path = DATA_DIR / f"{username}-report-{stamp}.md"
    latest_raw = DATA_DIR / f"{username}-latest-raw.json"
    latest_structured = DATA_DIR / f"{username}-latest.json"
    latest_report = DATA_DIR / f"{username}-latest-report.md"

    raw_payload = {
        "fetched_at": fetched_at,
        "user": user_payload,
        "tweets": tweets_payload,
    }
    structured_payload = {
        "fetched_at": fetched_at,
        "username": username,
        "user": user_payload.get("data", {}),
        "tweets": [asdict(tweet) for tweet in tweets],
    }

    for path, payload in [
        (raw_path, raw_payload),
        (latest_raw, raw_payload),
        (structured_path, structured_payload),
        (latest_structured, structured_payload),
    ]:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for path in [report_path, latest_report]:
        path.write_text(summary, encoding="utf-8")

    return {
        "raw": raw_path,
        "structured": structured_path,
        "report": report_path,
        "latest_structured": latest_structured,
        "latest_report": latest_report,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track recent X post performance for one account.")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="X username without @")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="How many recent posts to fetch (5-100)")
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    username = args.username.lstrip("@")
    ensure_dirs()
    bearer_token = require_bearer_token()
    fetched_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    user_payload = fetch_user(username, bearer_token)
    user_id = user_payload.get("data", {}).get("id")
    if not user_id:
        raise SystemExit(f"No user id returned for @{username}: {json.dumps(user_payload)[:400]}")

    tweets_payload = fetch_tweets(user_id, args.limit, bearer_token)
    tweets = normalize_tweets(username, tweets_payload)
    summary = build_summary(username, user_payload, tweets, fetched_at)
    paths = save_outputs(username, user_payload, tweets_payload, tweets, summary, fetched_at)
    append_performance_log(username, user_payload, tweets, fetched_at)

    print(summary)
    print("Saved files:")
    for key, path in paths.items():
        print(f"- {key}: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
