# Madlan Lead Scraping — Findings (2026-07-02)

## What the project does
Scrapes real-estate agency leads from madlan.co.il: pulls the agency directory
for a city, then visits each agency's profile page for name/phone/website.
Code already exists in `scraper/` (`madlan_client.py`, `directory_parser.py`,
`profile_parser.py`, `pipeline.py`). This doc is a status report on whether
that existing code actually works against the live site right now, tested
directly (not through the DB/webapp).

## Method used to test
Called the existing fetch functions directly against live madlan.co.il pages:
- `scraper.madlan_client.fetch_directory()` — requests-first, Firecrawl fallback
- `scraper.madlan_client.fetch_profile()` — same pattern
- Also called the Firecrawl SDK (`firecrawl.Firecrawl().scrape(...)`) directly
  with various options to isolate the profile-page problem.

## Result 1: Directory listing — WORKS
One Firecrawl call against
`https://www.madlan.co.il/madad-search/תל-אביב-יפו-ישראל` returned 39 real
agencies in a single response (1 credit):

```
re_office_hpsBJEb5HKJ | יש נדל"ן            | deals: 520 | exclusives: 39
re_office_c0Mox2Ev9BB | רימקס WIN           | deals: 136 | exclusives: 61
re_office_dMI4FvN1sRE | Nadlan ToGo         | deals: 156 | exclusives: 28
re_office_c49w6MoRyfA | דיפלורה נכסים        | deals: 573 | exclusives: 52
... (39 total)
```

Each stub includes: madlan office ID, name, deal count, exclusives count, and
profile URL. This part of `scraper/directory_parser.py` is solid.

## Result 2: Profile pages (phone/website) — BLOCKED most of the time
This is the part that gets you phone numbers and websites. It's currently
unreliable:

- Plain `requests` → HTTP 403 (blocked outright), on every attempt.
- Firecrawl (`fetch_profile`) → usually returns an empty "accessibility
  widget" shell — exactly 5060 bytes, no actual page content — instead of the
  real page (which is ~150-200KB with a `tel:` link, name, website).

Tried to fix it, none of it changed the outcome:
| Attempt | Result |
|---|---|
| wait_for 15s (current default) | shell (usually) |
| wait_for 20s / 25s / 30s | shell, every time |
| Firecrawl stealth proxy (5x credit cost) | shell |
| Israel geo-targeting (`location: {country: IL}`) | shell |
| 9 back-to-back retries on 3 different agencies | shell every single time |

Out of roughly 13 profile-page attempts across all these variations, only
**1** returned the real page. That 1 success came from a plain `wait_for:
15000` call with no special options — same as most of the failed attempts —
so this isn't a config problem, it's Madlan actively blocking/serving a
decoy page to Firecrawl's renderer on profile pages specifically (directory
pages aren't blocked the same way).

## Why this matters for the pipeline
`scraper/pipeline.py` calls `fetch_profile()` once per agency and treats a
non-2xx/shell result as a hard failure (logged to `failed_urls`, agency
skipped). At today's ~8% success rate, scraping 50 agencies would burn
roughly 13x the expected Firecrawl credits and still fail to save most of
them — not viable as-is.

## Recommendation for next steps (not yet implemented)
Options to make profile-page fetching reliable, roughly in order of effort:
1. **Retry loop with a cap** (e.g. up to 5 attempts, stop early on success) —
   cheapest code change, but at ~8% hit rate could still cost ~12 credits/
   profile on average. Worth confirming the true success rate isn't just bad
   luck from hitting the same 3 URLs repeatedly in a short window (possible
   rate-limit escalation from our own burst of test traffic).
2. **A real local browser (Playwright/Selenium) instead of Firecrawl** for
   profile pages — full control over waits, mouse movement, and fingerprint;
   Firecrawl's renderer may simply be recognized and blocked as an automation
   tool regardless of proxy tier.
3. **Look for Madlan's underlying data API** — the profile page is React/Next
   rendered; there may be a JSON endpoint the frontend calls (`__NEXT_DATA__`
   or an XHR/GraphQL call) that returns phone/website directly without
   needing a rendered page at all. Not yet investigated.
4. **Space out requests more / vary timing** — if this is rate-limit-based
   rather than a hard per-request block, slowing down and spreading requests
   over a longer session (vs. ~13 requests in ~10 minutes as done here) might
   change the hit rate. Untested.

## Credits spent during this test session
~21 Firecrawl credits (on top of 29 already used in earlier development),
all on diagnostics — no leads were saved to the database during this test.
