# Bulk Scheduler for Facebook, Instagram, TikTok (free)

This posts your content automatically on a schedule, for $0/month, using
GitHub Actions to run the script and a public GitHub repo to host your
media files.

## 1. Create the repo
1. Create a **public** GitHub repo (free account is fine) — public is
   required so raw.githubusercontent.com links work as public media URLs.
   Only put content in it you're fine being publicly fetchable; this is
   normal since it's about to be posted publicly anyway.
2. Upload these files (`bulk_scheduler.py`, `posts.csv`, `.github/workflows/scheduler.yml`)
   to the repo, plus a `media/` folder with your images/videos.

## 2. Get your Meta (Facebook + Instagram) credentials — free
1. Go to developers.facebook.com → My Apps → Create App → choose "Business."
2. In the app, add the **Facebook Login** and **Instagram Graph API** products.
3. Under Tools → Graph API Explorer:
   - Select your app, select your Page, and generate a **Page Access Token**
     with `pages_manage_posts`, `pages_read_engagement`, and (for Instagram)
     `instagram_content_publish` permissions.
   - Note your **Page ID** (found in Page Settings) and your **Instagram
     Business Account ID** (Page Settings → Linked Accounts, or via
     `GET /{page-id}?fields=instagram_business_account`).
4. Short-lived tokens expire in ~1 hour. For an always-working automation,
   exchange it for a **long-lived token** (60 days) via the
   `/oauth/access_token?grant_type=fb_exchange_token` endpoint, or submit
   for App Review to get a token that doesn't expire. Meta's docs walk
   through this — search "Facebook long-lived page access token."

## 3. Get your TikTok credentials — free
1. Go to developers.tiktok.com → register → create an app.
2. Add the **Content Posting API** product.
3. Generate an access token via TikTok's OAuth flow for your creator account.
4. **Until your app passes TikTok's content-posting audit**, posts will
   arrive as **private drafts** in the creator's TikTok inbox — they'll
   need to open the app and tap "Post" to finish. This is a TikTok
   restriction on unaudited apps, not something the script can bypass.
   Submitting for audit is free; approval usually takes a few days once
   you demonstrate real usage.

## 4. Add your credentials as GitHub Secrets
In your repo: Settings → Secrets and variables → Actions → New repository secret.
Add each of:
- `FB_PAGE_ID`
- `FB_PAGE_ACCESS_TOKEN`
- `IG_BUSINESS_ID`
- `IG_ACCESS_TOKEN`
- `TIKTOK_ACCESS_TOKEN`

## 5. Fill in posts.csv
Edit `posts.csv` (columns: platform, date, time, caption, media_filename,
status). Times are in **UTC** — convert your local time before entering it.
Leave `status` as `pending`; the script updates it automatically after
each attempt (`posted: <id>` or `failed: <reason>`).

## 6. Done
GitHub Actions runs the script every 15 minutes automatically, checks for
anything due, and publishes it. You can also trigger it manually anytime
from the repo's **Actions** tab → "Bulk Social Scheduler" → "Run workflow."

## Notes
- Facebook posts natively; Instagram and TikTok publish the moment the
  script sees they're due (usually within 15 min of your scheduled time).
- If a post fails (bad token, expired media URL, etc.), check the
  `status` column in posts.csv after the run — the error message will be
  right there.
- Long-lived Meta tokens expire every 60 days unless you complete App
  Review; set yourself a reminder to refresh it.
