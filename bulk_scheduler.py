"""
Bulk social scheduler for Facebook, Instagram, and TikTok.

HOW IT WORKS
------------
This script is meant to run on a schedule (every 15-30 min, via GitHub
Actions cron or your own cron/Task Scheduler). Each run it:
  1. Reads posts.csv
  2. Finds rows whose date+time has arrived and status == "pending"
  3. Publishes them to the right platform
  4. Marks them "posted" (or "failed: <reason>") and re-saves the CSV

MEDIA
-----
media_filename in the CSV should be a path relative to this repo, e.g.
"media/post1.jpg". The script converts that into a public raw GitHub URL
using GITHUB_REPO / GITHUB_BRANCH env vars, since Instagram and TikTok
need a publicly reachable URL (they can't accept a raw file upload from
your computer, only Facebook photos can).

Facebook still works fine with these public URLs too, so we use the same
approach for all three platforms for consistency.

REQUIRED ENVIRONMENT VARIABLES (set as GitHub Secrets, see README.md)
-----------------------------------------------------------------
  FB_PAGE_ID
  FB_PAGE_ACCESS_TOKEN
  IG_BUSINESS_ID
  IG_ACCESS_TOKEN            (usually same as FB_PAGE_ACCESS_TOKEN)
  TIKTOK_ACCESS_TOKEN
  GITHUB_REPO                e.g. "yourname/bulk-scheduler"
  GITHUB_BRANCH               e.g. "main"
"""

import csv
import os
import sys
from datetime import datetime, timezone

import requests

CSV_PATH = "posts.csv"
GRAPH_VERSION = "v21.0"

FB_PAGE_ID = os.environ.get("FB_PAGE_ID")
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN")
IG_BUSINESS_ID = os.environ.get("IG_BUSINESS_ID")
IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN")
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")


def public_media_url(media_filename: str) -> str:
    """Turn a repo-relative file path into a public raw GitHub URL."""
    if not GITHUB_REPO:
        raise RuntimeError("GITHUB_REPO env var is not set.")
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{media_filename}"


def is_due(date_str: str, time_str: str) -> bool:
    scheduled = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    scheduled = scheduled.replace(tzinfo=timezone.utc)  # keep CSV times in UTC
    return datetime.now(timezone.utc) >= scheduled


def post_to_facebook(caption: str, media_url: str) -> str:
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{FB_PAGE_ID}/photos"
    resp = requests.post(url, data={
        "url": media_url,
        "caption": caption,
        "access_token": FB_PAGE_ACCESS_TOKEN,
    })
    resp.raise_for_status()
    return resp.json().get("post_id", resp.json().get("id", "ok"))


def post_to_instagram(caption: str, media_url: str) -> str:
    # Step 1: create media container
    container_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{IG_BUSINESS_ID}/media"
    resp = requests.post(container_url, data={
        "image_url": media_url,
        "caption": caption,
        "access_token": IG_ACCESS_TOKEN,
    })
    resp.raise_for_status()
    creation_id = resp.json()["id"]

    # Step 2: publish it
    publish_url = f"https://graph.facebook.com/{GRAPH_VERSION}/{IG_BUSINESS_ID}/media_publish"
    resp = requests.post(publish_url, data={
        "creation_id": creation_id,
        "access_token": IG_ACCESS_TOKEN,
    })
    resp.raise_for_status()
    return resp.json().get("id", "ok")


def post_to_tiktok(caption: str, media_url: str) -> str:
    """
    NOTE: Until your TikTok app passes content-posting audit, videos posted
    this way land as a PRIVATE DRAFT in the creator's TikTok inbox -- the
    creator must open the TikTok app and tap "Post" manually. This is a
    TikTok platform restriction for unaudited apps, not a script bug.
    Once audited, change "post_mode" logic on TikTok's side (your app's
    approved settings) to allow direct publish.
    """
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "post_info": {
            "title": caption,
            "privacy_level": "SELF_ONLY",  # required for unaudited apps
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": media_url,
        },
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json().get("data", {}).get("publish_id", "ok")


PUBLISHERS = {
    "facebook": post_to_facebook,
    "instagram": post_to_instagram,
    "tiktok": post_to_tiktok,
}


def main():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    changed = False
    for row in rows:
        if row["status"] != "pending":
            continue
        if not is_due(row["date"], row["time"]):
            continue

        platform = row["platform"].strip().lower()
        publisher = PUBLISHERS.get(platform)
        if not publisher:
            row["status"] = f"failed: unknown platform '{platform}'"
            changed = True
            continue

        try:
            media_url = public_media_url(row["media_filename"].strip())
            result_id = publisher(row["caption"], media_url)
            row["status"] = f"posted: {result_id}"
            print(f"[OK] {platform} -> {result_id}")
        except Exception as exc:
            row["status"] = f"failed: {exc}"
            print(f"[FAIL] {platform}: {exc}", file=sys.stderr)
        changed = True

    if changed:
        with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print("posts.csv updated with results.")
    else:
        print("No due posts this run.")


if __name__ == "__main__":
    main()
